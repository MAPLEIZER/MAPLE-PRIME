export type NavigationId =
  | "overview"
  | "institutions"
  | "requests"
  | "evidence"
  | "cases"
  | "reports"
  | "legal"
  | "civic";

export const navigationItems: ReadonlyArray<{ id: NavigationId; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "institutions", label: "Institutions" },
  { id: "requests", label: "My requests" },
  { id: "evidence", label: "Evidence" },
  { id: "cases", label: "Cases" },
  { id: "reports", label: "Reports" },
  { id: "legal", label: "Legal Library" },
  { id: "civic", label: "Civic Participation" },
];

export type DiscrepancyKind =
  | "not_located"
  | "candidate_match"
  | "source_stale"
  | "verified_difference";

const discrepancyLabels: Record<DiscrepancyKind, string> = {
  not_located: "Not located in reviewed source",
  candidate_match: "Candidate match — review required",
  source_stale: "Source snapshot may be stale",
  verified_difference: "Verified source difference",
};

export function discrepancyLabel(kind: DiscrepancyKind): string {
  return discrepancyLabels[kind];
}
