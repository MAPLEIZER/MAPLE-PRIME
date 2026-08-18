import type { ReconciliationFinding } from "@/api/dashboard";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";

function title(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function reviewLabel(value: string): string {
  if (value === "pending") return "Pending review";
  if (value === "confirmed") return "Confirmed match";
  if (value === "rejected") return "Rejected match";
  return title(value);
}

export function ReportsPage({
  findings,
  unavailable = false,
  reviewingId = null,
  onReview,
}: {
  findings: ReconciliationFinding[];
  unavailable?: boolean;
  reviewingId?: string | null;
  onReview?: (findingId: string, decision: "confirmed" | "rejected") => void;
}) {
  return (
    <div className="space-y-5">
      <Card>
        <CardHeader>
          <CardTitle>CBK ↔ ODPC reconciliation</CardTitle>
          <CardDescription>
            Candidate matching between the latest persisted regulator snapshots. Findings are evidence-management records, not compliance determinations.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {unavailable ? (
            <div className="rounded-lg border border-border bg-muted/50 px-4 py-3 text-xs text-muted-foreground">
              Reconciliation findings are currently unavailable. No cached result is being presented as current.
            </div>
          ) : findings.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border bg-muted/30 p-8 text-center">
              <div className="text-sm font-medium">No reconciliation findings yet</div>
              <p className="mb-0 mt-1 text-xs text-muted-foreground">Sync CBK and ODPC sources from Overview to generate the review queue.</p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-border">
              <table className="w-full min-w-[980px] border-collapse text-left text-xs">
                <thead className="bg-muted/60 text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 font-medium">Finding</th>
                    <th className="px-3 py-2 font-medium">Review</th>
                    <th className="px-3 py-2 font-medium">Confidence</th>
                    <th className="px-3 py-2 font-medium">Evidence summary</th>
                    <th className="px-3 py-2 font-medium">Source keys</th>
                    <th className="px-3 py-2 font-medium">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {findings.map((finding) => (
                    <tr key={finding.id} className="align-top">
                      <td className="px-3 py-3 font-medium">{title(finding.finding_type)}</td>
                      <td className="px-3 py-3"><Badge>{reviewLabel(finding.review_state)}</Badge></td>
                      <td className="px-3 py-3 tabular-nums">{Math.round(finding.confidence * 100)}%</td>
                      <td className="max-w-md px-3 py-3 leading-5 text-muted-foreground">{finding.summary}</td>
                      <td className="px-3 py-3 font-mono text-[10px] leading-4 text-muted-foreground">
                        <div>{finding.left_source_key}</div>
                        <div>{finding.right_source_key ?? "ODPC record not located"}</div>
                      </td>
                      <td className="px-3 py-3">
                        {finding.review_state === "pending" && onReview ? (
                          <div className="flex gap-2">
                            <Button
                              className="h-8 px-2 text-xs"
                              disabled={reviewingId === finding.id}
                              onClick={() => onReview(finding.id, "confirmed")}
                            >
                              Confirm
                            </Button>
                            <Button
                              className="h-8 bg-card px-2 text-xs text-foreground"
                              disabled={reviewingId === finding.id}
                              onClick={() => onReview(finding.id, "rejected")}
                            >
                              Reject
                            </Button>
                          </div>
                        ) : (
                          <span className="text-muted-foreground">Reviewed</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
