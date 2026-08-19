import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { PricingPage } from "./PricingPage";

const apps = [{
  id: "app-123",
  store: "google_play",
  package_name: "ke.co.example.loan",
  loan_relevance: "candidate",
  first_seen_at: "2026-08-18T10:00:00Z",
  last_seen_at: "2026-08-19T10:00:00Z",
  app_name: "Example Cash",
  developer_name: "Example Credit Limited",
  developer_id: null,
  support_email: "support@example.co.ke",
  email_domain: "example.co.ke",
  developer_website: "https://example.co.ke",
  developer_domain: "example.co.ke",
  privacy_policy_url: null,
  store_url: "https://play.google.com/store/apps/details?id=ke.co.example.loan",
  category: "Finance",
  installs: "10,000+",
  source_provider: "fixture",
  source_url: "https://example.co.ke/source",
  observed_at: "2026-08-19T10:00:00Z",
  ownership_links: [],
}];

const records = [{
  id: "pricing-1",
  app_id: "app-123",
  institution_id: null,
  source_type: "public_disclosure",
  source_provider: "provider website",
  source_url: "https://example.co.ke/terms",
  observed_at: "2026-08-19T10:00:00Z",
  currency: "KES",
  amount_received: "5000.00",
  total_repayment: "6050.00",
  term_days: 30,
  advertised_interest_rate_percent: "10.0000",
  advertised_rate_basis: "term",
  interest_amount: "500.00",
  processing_fee: "250.00",
  service_fee: "200.00",
  insurance_fee: "100.00",
  disbursement_fee: "0.00",
  other_mandatory_fees: "0.00",
  disclosed_late_fee: "0.00",
  disclosed_rollover_fee: "0.00",
  effective_cost_amount: "1050.00",
  effective_cost_percent: "21.0000",
  known_cost_amount: "1050.00",
  unexplained_cost_amount: "0.00",
}];

describe("PricingPage", () => {
  it("shows period cost, fee composition, source provenance and APR warning", () => {
    const html = renderToStaticMarkup(
      <PricingPage
        apps={apps}
        records={records}
        unavailable={false}
        saving={false}
        onSelectApp={vi.fn()}
        onRecord={vi.fn()}
      />,
    );

    expect(html).toContain("Loan Pricing Intelligence");
    expect(html).toContain("21.00%");
    expect(html).toContain("KES 1,050.00");
    expect(html).toContain("30 days");
    expect(html).toContain("provider website");
    expect(html).toContain("not APR");
    expect(html).toContain("Unexplained cost");
    expect(html).toContain("Record pricing observation");
  });
});
