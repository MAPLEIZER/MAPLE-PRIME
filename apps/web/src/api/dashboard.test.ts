import { afterEach, describe, expect, it, vi } from "vitest";
import {
  loadDashboardSummary,
  loadReconciliationFindings,
  reviewFinding,
  runReconciliation,
  syncAlphaSources,
  syncSource,
} from "./dashboard";


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

  it("loads auditable reconciliation findings", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ([{
        id: "finding-1",
        finding_type: "not_located",
        confidence: 1,
        summary: "Matching ODPC record not located in the reviewed source snapshot.",
        review_state: "pending",
        left_source_key: "cbk-snapshot:17",
        right_source_key: null,
        reviewed_by: null,
        reviewed_at: null,
      }]),
    });
    vi.stubGlobal("fetch", fetchMock);

    const findings = await loadReconciliationFindings();
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/reconciliation/findings?limit=500", { signal: undefined });
    expect(findings[0].left_source_key).toBe("cbk-snapshot:17");
    expect(findings[0].review_state).toBe("pending");
  });

  it("fails closed on a non-success response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    await expect(loadDashboardSummary()).rejects.toThrow("dashboard summary request failed");
  });

  it("syncs only through the explicit local-action contract", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ source_id: "cbk_dcp", snapshot_id: "1", sha256: "abc", record_count: 252 }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await syncSource("cbk_dcp");
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/sources/cbk_dcp/sync", {
      method: "POST",
      headers: { "X-KDR-Local-Action": "sync" },
    });
    expect(result.record_count).toBe(252);
  });

  it("surfaces the API's bounded source failure reason without raw response text", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
      json: async () => ({
        detail: {
          source_id: "odpc_registered",
          code: "source_access_restricted",
          message: "The official source refused automated access. Retry later or open the official source manually.",
        },
      }),
    }));

    await expect(syncSource("odpc_registered")).rejects.toMatchObject({
      name: "SourceSyncError",
      sourceId: "odpc_registered",
      code: "source_access_restricted",
      message: "The official source refused automated access. Retry later or open the official source manually.",
    });
  });

  it("uses a distinct explicit action for reconciliation", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ cbk_snapshot_id: "cbk-1", odpc_snapshot_id: "odpc-1", finding_count: 252 }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await runReconciliation();
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/reconciliation/cbk-odpc/run", {
      method: "POST",
      headers: { "X-KDR-Local-Action": "reconcile" },
    });
    expect(result.finding_count).toBe(252);
  });

  it("uses a distinct explicit action for manual review", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: "finding-1", review_state: "confirmed", reviewed_by: "local_user" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await reviewFinding("finding-1", "confirmed");
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/reconciliation/findings/finding-1/review", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-KDR-Local-Action": "review" },
      body: JSON.stringify({ decision: "confirmed" }),
    });
    expect(result.review_state).toBe("confirmed");
  });

  it("runs reconciliation after both alpha sources sync successfully and emits stage progress", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ source_id: "cbk_dcp", snapshot_id: "1", sha256: "a", record_count: 252 }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ source_id: "odpc_registered", snapshot_id: "2", sha256: "b", record_count: 10 }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ cbk_snapshot_id: "1", odpc_snapshot_id: "2", finding_count: 252 }) });
    vi.stubGlobal("fetch", fetchMock);
    const stages: string[] = [];

    const report = await syncAlphaSources((event) => stages.push(`${event.stage}:${event.state}`));
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[2][0]).toBe("/api/v1/reconciliation/cbk-odpc/run");
    expect(report.failures).toEqual([]);
    expect(report.succeeded).toEqual(["cbk_dcp", "odpc_registered", "reconciliation"]);
    expect(stages).toEqual([
      "cbk_dcp:running",
      "cbk_dcp:success",
      "odpc_registered:running",
      "odpc_registered:success",
      "reconciliation:running",
      "reconciliation:success",
    ]);
  });

  it("preserves CBK success, reports ODPC reason, and skips reconciliation on partial failure", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ source_id: "cbk_dcp", snapshot_id: "1", sha256: "abc", record_count: 252 }),
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 502,
        json: async () => ({
          detail: {
            source_id: "odpc_registered",
            code: "source_access_restricted",
            message: "The official source refused automated access. Retry later or open the official source manually.",
          },
        }),
      });
    vi.stubGlobal("fetch", fetchMock);
    const stages: string[] = [];

    const report = await syncAlphaSources((event) => stages.push(`${event.stage}:${event.state}`));
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(report.succeeded).toEqual(["cbk_dcp"]);
    expect(report.failures).toEqual([{
      stage: "odpc_registered",
      code: "source_access_restricted",
      message: "The official source refused automated access. Retry later or open the official source manually.",
    }]);
    expect(stages.at(-1)).toBe("reconciliation:skipped");
  });
});
