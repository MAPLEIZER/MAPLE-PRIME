import { afterEach, describe, expect, it, vi } from "vitest";
import { importPlayApps } from "./apps";

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();
});

describe("app registry API", () => {
  it("imports normalized public Play records only through an explicit local action", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ apps_touched: 1, observations_available: 1, ownership_candidates: 1 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    globalThis.fetch = fetchMock as typeof fetch;

    const records = [{
      store: "google_play",
      package_name: "ke.co.example.cash",
      app_name: "Example Cash",
      developer_name: "Example Credit Limited",
      store_url: "https://play.google.com/store/apps/details?id=ke.co.example.cash",
      source_provider: "fixture",
      source_url: "https://example.invalid/run/1",
      observed_at: "2026-08-19T10:00:00+00:00",
    }];
    const result = await importPlayApps(records);
    expect(result.apps_touched).toBe(1);
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/apps/import/play", expect.objectContaining({
      method: "POST",
      headers: expect.objectContaining({ "X-KDR-Local-Action": "import_apps" }),
    }));
  });
});
