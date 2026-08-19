import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { EvidencePage } from "./EvidencePage";


describe("evidence intelligence", () => {
  it("explains automated Play discovery, account health and BRS verification", () => {
    const html = renderToStaticMarkup(<EvidencePage />);
    expect(html).toContain("Google Play → CBK discovery");
    expect(html).toContain("Run discovery now");
    expect(html).toContain("Re-check account");
    expect(html).toContain("SerpApi");
    expect(html).toContain("BRS corporate evidence");
    expect(html).toContain("Official company search");
    expect(html).toContain("Upload BRS PDF");
    expect(html).toContain("security-question");
  });
});
