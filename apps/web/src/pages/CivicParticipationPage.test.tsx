import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CivicParticipationPage } from "./CivicParticipationPage";

const consultations = [
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
    render(<CivicParticipationPage consultations={consultations} unavailable={false} />);
    expect(screen.getByRole("heading", { name: /civic participation/i })).toBeInTheDocument();
    expect(screen.getByText(/official feedback form/i)).toBeInTheDocument();
    expect(screen.getByText(/never bulk-submit/i)).toBeInTheDocument();
  });
});
