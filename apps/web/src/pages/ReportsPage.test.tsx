import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ReportsPage } from "./ReportsPage";


describe("reconciliation report", () => {
  it("shows the regulator identities and match evidence instead of opaque IDs", () => {
    const html = renderToStaticMarkup(
      <ReportsPage
        findings={[
          {
            id: "finding-1",
            finding_type: "candidate_match",
            confidence: 0.96,
            summary: "Automatically confirmed exact normalized legal-name match.",
            review_state: "confirmed",
            left_source_key: "cbk-snapshot:17",
            right_source_key: "odpc-snapshot:INST-1:data_controller",
            reviewed_by: "system:auto_identity_threshold_v1",
            reviewed_at: "2026-08-19T12:00:00Z",
            match_basis: "normalized_legal_name_exact",
            auto_confirmed: true,
            cbk: {
              legal_name: "Example Credit Limited",
              trading_name: "Example Cash",
              website: "https://example.co.ke",
              emails: ["support@example.co.ke"],
            },
            odpc: {
              name: "Example Credit Ltd",
              registration_number: "INST-1",
              handler_type: "Data Controller",
              status: "Active/Renewed",
              county: "NAIROBI",
              country: "Kenya",
            },
          },
        ]}
        onReview={() => undefined}
      />,
    );

    expect(html).toContain("Example Credit Limited");
    expect(html).toContain("Example Credit Ltd");
    expect(html).toContain("INST-1");
    expect(html).toContain("Data Controller");
    expect(html).toContain("Exact legal-name match");
    expect(html).toContain("Auto-confirmed");
    expect(html).not.toContain("cbk-snapshot:17");
  });

  it("keeps lower-confidence or not-located evidence available for human review", () => {
    const html = renderToStaticMarkup(
      <ReportsPage
        findings={[
          {
            id: "finding-2",
            finding_type: "not_located",
            confidence: 1,
            summary: "Matching ODPC record not located in the reviewed source snapshot. This is an evidence gap, not a finding of non-registration or non-compliance.",
            review_state: "pending",
            left_source_key: "cbk-snapshot:18",
            right_source_key: null,
            reviewed_by: null,
            reviewed_at: null,
            match_basis: "not_located",
            auto_confirmed: false,
            cbk: { legal_name: "Missing Finance Limited", trading_name: null, website: null, emails: [] },
            odpc: null,
          },
        ]}
        onReview={() => undefined}
      />,
    );

    expect(html).toContain("Missing Finance Limited");
    expect(html).toContain("No ODPC record located");
    expect(html).toContain("Confirm");
    expect(html).toContain("Reject");
    expect(html).toContain("evidence gap");
  });
});
