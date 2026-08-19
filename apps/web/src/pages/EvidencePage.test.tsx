import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { EvidencePage } from "./EvidencePage";


describe("evidence intelligence", () => {
  it("explains multi-provider Play discovery and BRS verification", () => {
    const html = renderToStaticMarkup(<EvidencePage />);
    expect(html).toContain("Google Play → CBK discovery");
    expect(html).toContain("Run discovery now");
    expect(html).toContain("TalorData");
    expect(html).toContain("SerpApi.com");
    expect(html).toContain("KDR_PLAY_DISCOVERY_PROVIDER=talordata");
    expect(html).toContain("KDR_PLAY_DISCOVERY_PROVIDER=serpapi");
    expect(html).toContain("BRS corporate evidence");
    expect(html).toContain("Official company search");
    expect(html).toContain("Upload BRS PDF");
    expect(html).toContain("security-question");
  });
});
