import { AlertTriangle, FileCheck2, ShieldCheck } from "lucide-react";
import type { DashboardSummary } from "@/api/dashboard";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";

function Metric({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <Card>
      <CardHeader>
        <CardDescription>{label}</CardDescription>
        <div className="text-2xl font-semibold tracking-tight">{value}</div>
      </CardHeader>
      <CardContent className="text-xs text-muted-foreground">{note}</CardContent>
    </Card>
  );
}

export function OverviewPage({
  summary,
  unavailable = false,
}: {
  summary: DashboardSummary | null;
  unavailable?: boolean;
}) {
  const cbk = summary?.sources.cbk_dcp;
  const odpc = summary?.sources.odpc_registered;
  const sourceRows = [
    ["CBK", "DCP licensing and official contact records", cbk ? `Synced · ${cbk.record_count} records` : "Not synced"],
    ["ODPC", "Controller / processor registry observations", odpc ? `Synced · ${odpc.record_count} rows` : "Not synced"],
    ["CRB", "Regulatory status + subject evidence", "Model ready"],
    ["Kenya Law", "Legislation and court outcomes", "Source defined"],
  ] as const;

  return (
    <div className="space-y-5">
      {unavailable ? (
        <div className="rounded-lg border border-border bg-muted/50 px-4 py-3 text-xs text-muted-foreground">
          Local API status is unavailable. No cached regulator counts are being presented as current.
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric
          label="CBK DCP reference"
          value={summary?.counts.cbk_dcp_reference_count ? String(summary.counts.cbk_dcp_reference_count) : "Not synced"}
          note="Count comes from the latest persisted CBK source snapshot"
        />
        <Metric
          label="ODPC reconciliation"
          value={summary?.counts.odpc_synced ? "Synced" : "Not synced"}
          note="No compliance inference from missing matches"
        />
        <Metric
          label="Open rights requests"
          value={String(summary?.counts.open_requests ?? 0)}
          note="Targeted workflows only"
        />
        <Metric
          label="Manual review"
          value={String(summary?.counts.manual_review ?? 0)}
          note="Aliases, fuzzy matches and case outcomes"
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Regulatory source coverage</CardTitle>
            <CardDescription>Every synced observation is tied to a versioned source snapshot.</CardDescription>
          </CardHeader>
          <CardContent className="divide-y divide-border">
            {sourceRows.map(([name, detail, status]) => (
              <div key={name} className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0">
                <div>
                  <div className="text-sm font-medium">{name}</div>
                  <div className="text-xs text-muted-foreground">{detail}</div>
                </div>
                <Badge>{status}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-start gap-3">
            <AlertTriangle size={18} className="mt-0.5 text-warning" />
            <div>
              <CardTitle>Review queue</CardTitle>
              <CardDescription>Claims remain conservative until evidence supports them.</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="rounded-lg bg-muted p-3">
              <div className="text-sm font-medium">No automatic accusations</div>
              <p className="mb-0 mt-1 text-xs leading-5 text-muted-foreground">An unmatched regulator record means not located in the reviewed source snapshot, not unregistered or non-compliant.</p>
            </div>
            <div className="rounded-lg bg-muted p-3">
              <div className="text-sm font-medium">CRB evidence boundary</div>
              <p className="mb-0 mt-1 text-xs leading-5 text-muted-foreground">Public CRB status stays separate from proof that a lender submitted a particular person&apos;s data.</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between gap-4">
          <div>
            <CardTitle>My rights workflow</CardTitle>
            <CardDescription>Access, correction, erasure, objection and CRB dispute requests.</CardDescription>
          </div>
          <Button disabled>New request</Button>
        </CardHeader>
        <CardContent>
          <div className="grid min-h-32 place-items-center rounded-lg border border-dashed border-border bg-muted/40 p-6 text-center">
            <div>
              <FileCheck2 className="mx-auto mb-2 text-muted-foreground" size={26} />
              <div className="text-sm font-medium">No requests yet</div>
              <p className="mb-0 mt-1 text-xs text-muted-foreground">The alpha keeps sending disabled until preview, transmission and audit controls are wired end-to-end.</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <ShieldCheck size={15} /> Local-first defaults; sensitive telemetry is disabled.
      </div>
    </div>
  );
}
