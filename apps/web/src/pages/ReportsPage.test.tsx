import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ReportsPage } from "./ReportsPage";


describe("reconciliation report", () => {
  it("renders conservative findings with auditable source keys", () => {
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
      />,
    );

    expect(html).toContain("CBK ↔ ODPC reconciliation");
    expect(html).toContain("Not located");
    expect(html).toContain("Pending review");
    expect(html).toContain("cbk-snapshot:17");
    expect(html).toContain("evidence gap");
    expect(html).not.toContain("Violation");
  });
});
