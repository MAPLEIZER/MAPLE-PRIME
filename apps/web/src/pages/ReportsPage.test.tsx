import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ReportsPage } from "./ReportsPage";


describe("reconciliation report", () => {
  it("renders conservative findings with auditable source keys and review controls", () => {
    const html = renderToStaticMarkup(
      <ReportsPage
        findings={[
          {
            id: "finding-1",
            finding_type: "not_located",
            confidence: 1,
            summary: "Matching ODPC record not located in the reviewed source snapshot. This is an evidence gap, not a finding of non-registration or non-compliance.",
            review_state: "pending",
            left_source_key: "cbk-snapshot:17",
            right_source_key: null,
            reviewed_by: null,
            reviewed_at: null,
          },
        ]}
        onReview={() => undefined}
      />,
    );

    expect(html).toContain("CBK ↔ ODPC reconciliation");
    expect(html).toContain("Not located");
    expect(html).toContain("Pending review");
    expect(html).toContain("cbk-snapshot:17");
    expect(html).toContain("evidence gap");
    expect(html).toContain("Confirm");
    expect(html).toContain("Reject");
    expect(html).not.toContain("Violation");
  });

  it("does not render review buttons for an already resolved finding", () => {
    const html = renderToStaticMarkup(
      <ReportsPage
        findings={[
          {
            id: "finding-2",
            finding_type: "candidate_match",
            confidence: 0.96,
            summary: "Candidate match — manual review required.",
            review_state: "confirmed",
            left_source_key: "cbk-snapshot:18",
            right_source_key: "odpc-snapshot:INST-2:data_controller",
            reviewed_by: "local_user",
            reviewed_at: "2026-08-18T08:00:00Z",
          },
        ]}
        onReview={() => undefined}
      />,
    );
    expect(html).toContain("Confirmed match");
    expect(html).not.toContain(">Confirm<");
    expect(html).not.toContain(">Reject<");
  });
});
