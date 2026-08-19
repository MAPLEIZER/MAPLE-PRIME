import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { EvidencePage } from "./EvidencePage";


describe("evidence intelligence", () => {
  it("renders the configurable Play research console and BRS verification", () => {
    const html = renderToStaticMarkup(<EvidencePage />);
    expect(html).toContain("Google Play research console");
    expect(html).toContain("Finance category crawl");
    expect(html).toContain("Category + queries");
    expect(html).toContain("mkopo");
    expect(html).toContain("Maximum app identities");
    expect(html).toContain("Skip apps already complete in KDR");
    expect(html).toContain("missing an email remain eligible");
    expect(html).toContain("Run research");
    expect(html).toContain("TalorData");
    expect(html).toContain("SerpApi.com");
    expect(html).toContain("legacy CBK-seeded discovery");
    expect(html).toContain("BRS corporate evidence");
    expect(html).toContain("Official company search");
    expect(html).toContain("Upload BRS PDF");
    expect(html).toContain("security-question");
  });
});
