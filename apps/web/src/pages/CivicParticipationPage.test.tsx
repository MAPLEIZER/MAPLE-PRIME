import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { Consultation } from "@/api/knowledge";
import { CivicParticipationPage } from "./CivicParticipationPage";

const consultations: Consultation[] = [
  {
    id: "ai-policy-2026",
    title: "Draft Kenya AI and Emerging Technologies Policy",
    agency: "Ministry of ICT",
    status: "closed",
    deadline: "2026-08-04T23:59:59+03:00",
    topics: ["ai", "data privacy"],
    sourceUrl: "https://ict.go.ke/example",
    channels: [{ kind: "form", url: "https://ict.go.ke/form", label: "Official feedback form" }],
  },
];

describe("CivicParticipationPage", () => {
  it("shows official source, deadline and anti-spam review boundary", () => {
    const html = renderToStaticMarkup(
      <CivicParticipationPage consultations={consultations} unavailable={false} />,
    );
    expect(html).toContain("Civic Participation");
    expect(html).toContain("Official feedback form");
    expect(html).toContain("never bulk-submit");
    expect(html).toContain("Submission actions disabled");
  });
});
