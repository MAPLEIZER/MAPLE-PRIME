import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { LegalLibraryPage } from "./LegalLibraryPage";

const entries = [
  {
    id: "data-protection-act",
    title: "Data Protection Act",
    citation: "Cap. 411C",
    summary: "Rights, obligations, lawful processing and enforcement.",
    topics: ["privacy", "rights", "processing"],
    provisions: ["section 25", "section 26", "section 40"],
    sourceUrl: "https://new.kenyalaw.org/example",
    sourceDate: "2022-12-31",
    caution: "Educational summary; not legal advice.",
  },
];

describe("LegalLibraryPage", () => {
  it("renders searchable legal teaching material and source link", () => {
    const html = renderToStaticMarkup(<LegalLibraryPage entries={entries} unavailable={false} />);
    expect(html).toContain("Legal Library");
    expect(html).toContain("Search laws, rights, CRB, consent, cybercrime");
    expect(html).toContain("Data Protection Act");
    expect(html).toContain("not legal advice");
    expect(html).toContain("Official source");
  });
});
