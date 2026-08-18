import { afterEach, describe, expect, it, vi } from "vitest";
import { loadDashboardSummary } from "./dashboard";


afterEach(() => {
  vi.unstubAllGlobals();
});

describe("dashboard API client", () => {
  it("loads persisted regulatory summary from the versioned API", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        project_status: "alpha",
        counts: {
          cbk_dcp_reference_count: 252,
          odpc_synced: true,
          open_requests: 1,
          manual_review: 3,
        },
        sources: {
          cbk_dcp: { snapshot_id: "1", sha256: "abc", retrieved_at: "2026-08-18T08:00:00Z", record_count: 252 },
        },
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const summary = await loadDashboardSummary();
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/dashboard/summary", { signal: undefined });
    expect(summary.counts.cbk_dcp_reference_count).toBe(252);
    expect(summary.counts.odpc_synced).toBe(true);
  });

  it("fails closed on a non-success response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    await expect(loadDashboardSummary()).rejects.toThrow("dashboard summary request failed");
  });
});
