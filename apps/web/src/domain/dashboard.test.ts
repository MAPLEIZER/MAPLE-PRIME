import { describe, expect, it } from "vitest";
import { discrepancyLabel, navigationItems } from "./dashboard";

describe("dashboard domain", () => {
  it("uses conservative discrepancy language", () => {
    expect(discrepancyLabel("not_located")).toBe("Not located in reviewed source");
    expect(discrepancyLabel("candidate_match")).toBe("Candidate match — review required");
  });
  it("keeps the alpha navigation intentional and includes the app registry and teaching/civic modules", () => {
    expect(navigationItems.map((item) => item.id)).toEqual([
      "overview",
      "institutions",
      "loan_apps",
      "requests",
      "evidence",
      "cases",
      "reports",
      "legal",
      "civic",
    ]);
  });
});
