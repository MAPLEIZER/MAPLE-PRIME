import { AlertTriangle, FileCheck2, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";

const sources = [
  ["CBK", "DCP licensing and official contact records", "Parser ready"],
  ["ODPC", "Controller / processor registry observations", "Parser ready"],
  ["CRB", "Regulatory status + subject evidence", "Model ready"],
  ["Kenya Law", "Legislation and court outcomes", "Source defined"],
] as const;

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

export function OverviewPage() {
  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="CBK DCP reference" value="252" note="Official directory dated 9 Jul 2026" />
        <Metric label="ODPC reconciliation" value="Pending sync" note="No compliance inference from missing matches" />
        <Metric label="Open rights requests" value="0" note="Targeted workflows only" />
        <Metric label="Manual review" value="0" note="Aliases, fuzzy matches and case outcomes" />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Regulatory source coverage</CardTitle>
            <CardDescription>Every observation is tied to a versioned source snapshot.</CardDescription>
          </CardHeader>
          <CardContent className="divide-y divide-border">
            {sources.map(([name, detail, status]) => (
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
              <p className="mb-0 mt-1 text-xs text-muted-foreground">The alpha keeps sending disabled until persistence, preview and audit controls are wired end-to-end.</p>
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
