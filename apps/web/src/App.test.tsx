import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { App } from "./App";


describe("alpha dashboard shell", () => {
  it("renders the tested navigation and privacy posture", () => {
    const html = renderToStaticMarkup(<App />);
    for (const label of ["Overview", "Institutions", "My requests", "Evidence", "Cases", "Reports"]) {
      expect(html).toContain(label);
    }
    expect(html).toContain("Local-first");
    expect(html).toContain("No automatic accusations");
  });

  it("shows source provenance rather than a compliance score", () => {
    const html = renderToStaticMarkup(<App />);
    expect(html).toContain("CBK");
    expect(html).toContain("ODPC");
    expect(html).toContain("CRB");
    expect(html).not.toContain("Compliance score");
  });
});
