import { afterEach, describe, expect, it, vi } from "vitest";
import { loadPricing, recordPricing } from "./pricing";

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();
});

describe("loan pricing API", () => {
  it("filters pricing history by app id", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response("[]", { status: 200, headers: { "Content-Type": "application/json" } }),
    );
    globalThis.fetch = fetchMock as typeof fetch;

    await loadPricing("app-123");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/pricing?app_id=app-123",
      expect.objectContaining({ signal: undefined }),
    );
  });

  it("records pricing only through the dedicated explicit local action", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: "pricing-1" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    globalThis.fetch = fetchMock as typeof fetch;

    await recordPricing({
      app_id: "app-123",
      source_type: "public_disclosure",
      source_provider: "manual research",
      source_url: "https://example.co.ke/terms",
      observed_at: "2026-08-19T12:00:00+03:00",
      currency: "KES",
      amount_received: "5000.00",
      total_repayment: "6050.00",
      term_days: 30,
      advertised_interest_rate_percent: "10.00",
      advertised_rate_basis: "term",
      interest_amount: "500.00",
      processing_fee: "250.00",
      service_fee: "200.00",
      insurance_fee: "100.00",
      disbursement_fee: "0.00",
      other_mandatory_fees: "0.00",
      disclosed_late_fee: "0.00",
      disclosed_rollover_fee: "0.00",
    });

    expect(fetchMock).toHaveBeenCalledWith("/api/v1/pricing", expect.objectContaining({
      method: "POST",
      headers: expect.objectContaining({ "X-KDR-Local-Action": "record_pricing" }),
    }));
  });
});
