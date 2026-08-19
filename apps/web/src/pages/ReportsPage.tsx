import type { ReconciliationFinding } from "@/api/dashboard";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";

function title(value: string): string {
  return value.split("_").map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");
}

function reviewLabel(finding: ReconciliationFinding): string {
  if (finding.auto_confirmed) return "Auto-confirmed";
  if (finding.review_state === "pending") return "Pending review";
  if (finding.review_state === "confirmed") return "Confirmed match";
  if (finding.review_state === "rejected") return "Rejected match";
  return title(finding.review_state);
}

function matchBasis(value: string): string {
  if (value === "normalized_legal_name_exact") return "Exact legal-name match";
  if (value === "normalized_trading_name_exact") return "Exact trading-name match";
  if (value === "legal_name_fuzzy") return "Fuzzy legal-name match";
  if (value === "not_located") return "No matching ODPC identity located";
  return title(value);
}

export function ReportsPage({ findings, unavailable = false, reviewingId = null, onReview }: {
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
            Compare the actual regulator identities below. Exact normalized legal/trading-name matches at 90% or above are auto-confirmed; evidence gaps and lower-confidence matches stay in the human review queue. These are identity links, not compliance determinations.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {unavailable ? (
            <div className="rounded-lg border border-border bg-muted/50 px-4 py-3 text-xs text-muted-foreground">Reconciliation findings are currently unavailable. No cached result is being presented as current.</div>
          ) : findings.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border bg-muted/30 p-8 text-center"><div className="text-sm font-medium">No reconciliation findings yet</div><p className="mb-0 mt-1 text-xs text-muted-foreground">Sync CBK and ODPC sources from Overview to generate the review queue.</p></div>
          ) : (
            <div className="space-y-3">
              {findings.map((finding) => (
                <div key={finding.id} className="rounded-xl border border-border bg-card p-4">
                  <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-semibold">{finding.cbk.legal_name ?? "Unnamed CBK record"}</span>
                        <Badge>{reviewLabel(finding)}</Badge>
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">{matchBasis(finding.match_basis)} · {Math.round(finding.confidence * 100)}% confidence</div>
                    </div>
                    {finding.review_state === "pending" && onReview ? (
                      <div className="flex gap-2">
                        <Button className="h-8 px-3 text-xs" disabled={reviewingId === finding.id} onClick={() => onReview(finding.id, "confirmed")}>Confirm</Button>
                        <Button className="h-8 bg-card px-3 text-xs text-foreground" disabled={reviewingId === finding.id} onClick={() => onReview(finding.id, "rejected")}>Reject</Button>
                      </div>
                    ) : null}
                  </div>

                  <div className="grid gap-3 md:grid-cols-[1fr_auto_1fr] md:items-stretch">
                    <div className="rounded-lg bg-muted/35 p-3">
                      <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">CBK licensed DCP record</div>
                      <div className="text-sm font-medium">{finding.cbk.legal_name ?? "Name unavailable"}</div>
                      {finding.cbk.trading_name ? <div className="mt-1 text-xs">Trading as: {finding.cbk.trading_name}</div> : null}
                      {finding.cbk.website ? <div className="mt-1 break-all text-xs text-muted-foreground">{finding.cbk.website}</div> : null}
                      {finding.cbk.emails.length > 0 ? <div className="mt-1 break-all text-xs text-muted-foreground">{finding.cbk.emails.join(", ")}</div> : null}
                    </div>
                    <div className="flex items-center justify-center px-2 text-xs font-semibold text-muted-foreground">↔</div>
                    <div className="rounded-lg bg-muted/35 p-3">
                      <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">ODPC registered-handler record</div>
                      {finding.odpc ? (
                        <>
                          <div className="text-sm font-medium">{finding.odpc.name ?? "Name unavailable"}</div>
                          <div className="mt-1 text-xs">Registration: {finding.odpc.registration_number ?? "Not supplied"}</div>
                          <div className="mt-1 text-xs">Role: {finding.odpc.handler_type ?? "Not supplied"}</div>
                          <div className="mt-1 text-xs text-muted-foreground">Status: {finding.odpc.status ?? "Not supplied"}{finding.odpc.county ? ` · ${finding.odpc.county}` : ""}</div>
                        </>
                      ) : (
                        <div className="text-sm font-medium">No ODPC record located</div>
                      )}
                    </div>
                  </div>

                  <div className="mt-3 rounded-lg border border-border/70 px-3 py-2 text-xs leading-5 text-muted-foreground">
                    <span className="font-medium text-foreground">Why this result: </span>{finding.summary}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
