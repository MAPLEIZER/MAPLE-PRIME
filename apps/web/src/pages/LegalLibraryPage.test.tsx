import { render, screen } from "@testing-library/react";
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
    render(<LegalLibraryPage entries={entries} unavailable={false} />);
    expect(screen.getByRole("heading", { name: /legal library/i })).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/search laws/i)).toBeInTheDocument();
    expect(screen.getByText(/data protection act/i)).toBeInTheDocument();
    expect(screen.getByText(/not legal advice/i)).toBeInTheDocument();
  });
});
