import { ExternalLink, PlusCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import type { LoanAppRecord } from "@/api/apps";
import type { LoanPricingInput, LoanPricingRecord } from "@/api/pricing";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";

const inputClass = "h-10 w-full rounded-md border border-border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring";
const labelClass = "space-y-1 text-xs font-medium text-muted-foreground";

function money(currency: string, value: string): string {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return `${currency} ${value}`;
  return `${currency} ${amount.toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function percent(value: string | null): string {
  if (value === null) return "Not disclosed";
  const amount = Number(value);
  return Number.isFinite(amount) ? `${amount.toFixed(2)}%` : `${value}%`;
}

function nonZeroFees(record: LoanPricingRecord): string[] {
  const fees: Array<[string, string]> = [
    ["Interest", record.interest_amount],
    ["Processing", record.processing_fee],
    ["Service", record.service_fee],
    ["Insurance", record.insurance_fee],
    ["Disbursement", record.disbursement_fee],
    ["Other mandatory", record.other_mandatory_fees],
  ];
  return fees.filter(([, value]) => Number(value) > 0).map(([label, value]) => `${label}: ${money(record.currency, value)}`);
}

type PricingPageProps = {
  apps: LoanAppRecord[];
  records: LoanPricingRecord[];
  unavailable: boolean;
  saving: boolean;
  selectedAppId?: string;
  onSelectApp: (appId: string) => void | Promise<void>;
  onRecord: (payload: LoanPricingInput) => void | Promise<void>;
};

export function PricingPage({
  apps,
  records,
  unavailable,
  saving,
  selectedAppId,
  onSelectApp,
  onRecord,
}: PricingPageProps) {
  const [appId, setAppId] = useState(selectedAppId ?? apps[0]?.id ?? "");
  const [sourceProvider, setSourceProvider] = useState("manual research");
  const [sourceUrl, setSourceUrl] = useState("");
  const [amountReceived, setAmountReceived] = useState("5000.00");
  const [totalRepayment, setTotalRepayment] = useState("6050.00");
  const [termDays, setTermDays] = useState("30");
  const [advertisedRate, setAdvertisedRate] = useState("");
  const [rateBasis, setRateBasis] = useState<LoanPricingInput["advertised_rate_basis"]>("unspecified");
  const [interestAmount, setInterestAmount] = useState("0.00");
  const [processingFee, setProcessingFee] = useState("0.00");
  const [serviceFee, setServiceFee] = useState("0.00");
  const [insuranceFee, setInsuranceFee] = useState("0.00");
  const [disbursementFee, setDisbursementFee] = useState("0.00");
  const [otherFees, setOtherFees] = useState("0.00");
  const [lateFee, setLateFee] = useState("0.00");
  const [rolloverFee, setRolloverFee] = useState("0.00");

  useEffect(() => {
    if (selectedAppId !== undefined) setAppId(selectedAppId);
    else if (!appId && apps[0]) setAppId(apps[0].id);
  }, [apps, appId, selectedAppId]);

  const appNames = useMemo(
    () => new Map(apps.map((app) => [app.id, app.app_name ?? app.package_name])),
    [apps],
  );

  const latest = records[0] ?? null;

  function selectApp(value: string) {
    setAppId(value);
    void onSelectApp(value);
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!appId) return;
    const parsedTerm = Number.parseInt(termDays, 10);
    if (!Number.isFinite(parsedTerm) || parsedTerm < 1) return;
    void onRecord({
      app_id: appId,
      source_type: "public_disclosure",
      source_provider: sourceProvider.trim(),
      source_url: sourceUrl.trim() || null,
      observed_at: new Date().toISOString(),
      currency: "KES",
      amount_received: amountReceived,
      total_repayment: totalRepayment,
      term_days: parsedTerm,
      advertised_interest_rate_percent: advertisedRate.trim() || null,
      advertised_rate_basis: rateBasis,
      interest_amount: interestAmount,
      processing_fee: processingFee,
      service_fee: serviceFee,
      insurance_fee: insuranceFee,
      disbursement_fee: disbursementFee,
      other_mandatory_fees: otherFees,
      disclosed_late_fee: lateFee,
      disclosed_rollover_fee: rolloverFee,
    });
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Loan Pricing Intelligence</CardTitle>
          <CardDescription>
            Compare what a borrower actually receives with total repayment and disclosed mandatory charges. Effective cost is measured over the observed loan term; it is not APR and is not a provider ranking.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          <div className="rounded-lg border border-border p-4">
            <div className="text-2xl font-semibold">{records.length}</div>
            <div className="text-xs text-muted-foreground">Pricing observations in view</div>
          </div>
          <div className="rounded-lg border border-border p-4">
            <div className="text-2xl font-semibold">{latest ? percent(latest.effective_cost_percent) : "—"}</div>
            <div className="text-xs text-muted-foreground">Latest effective period cost</div>
          </div>
          <div className="rounded-lg border border-border p-4">
            <div className="text-2xl font-semibold">{latest ? `${latest.term_days} days` : "—"}</div>
            <div className="text-xs text-muted-foreground">Latest observed term</div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Pricing history</CardTitle>
          <CardDescription>Select a tracked app to inspect its append-only pricing evidence.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <select
            className={inputClass}
            aria-label="Select tracked loan app"
            value={appId}
            onChange={(event) => selectApp(event.target.value)}
          >
            <option value="">All tracked apps</option>
            {apps.map((app) => <option key={app.id} value={app.id}>{app.app_name ?? app.package_name}</option>)}
          </select>
          {unavailable ? <div className="text-sm text-destructive">Pricing evidence could not be loaded.</div> : null}
          {!unavailable && records.length === 0 ? <div className="text-sm text-muted-foreground">No pricing observation has been recorded for this view.</div> : null}
          <div className="space-y-3">
            {records.map((record) => {
              const fees = nonZeroFees(record);
              return (
                <div key={record.id} className="rounded-lg border border-border bg-card p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="font-medium">{appNames.get(record.app_id) ?? record.app_id}</div>
                      <div className="text-xs text-muted-foreground">Observed {new Date(record.observed_at).toLocaleDateString()} · {record.term_days} days</div>
                    </div>
                    <Badge>{percent(record.effective_cost_percent)} period cost</Badge>
                  </div>
                  <div className="mt-4 grid gap-3 text-sm md:grid-cols-2 xl:grid-cols-4">
                    <div><div className="text-xs text-muted-foreground">Amount received</div><div>{money(record.currency, record.amount_received)}</div></div>
                    <div><div className="text-xs text-muted-foreground">Total repayment</div><div>{money(record.currency, record.total_repayment)}</div></div>
                    <div><div className="text-xs text-muted-foreground">Effective cost</div><div>{money(record.currency, record.effective_cost_amount)}</div></div>
                    <div><div className="text-xs text-muted-foreground">Advertised rate</div><div>{percent(record.advertised_interest_rate_percent)} · {record.advertised_rate_basis}</div></div>
                  </div>
                  <div className="mt-3 grid gap-3 md:grid-cols-2">
                    <div className="rounded-md bg-muted/40 p-3 text-sm">
                      <div className="text-xs font-medium text-muted-foreground">Known cost composition</div>
                      <div className="mt-1">{fees.length ? fees.join(" · ") : "No component fees were recorded."}</div>
                    </div>
                    <div className="rounded-md bg-muted/40 p-3 text-sm">
                      <div className="text-xs font-medium text-muted-foreground">Unexplained cost</div>
                      <div className="mt-1">{money(record.currency, record.unexplained_cost_amount)}</div>
                    </div>
                  </div>
                  {(Number(record.disclosed_late_fee) > 0 || Number(record.disclosed_rollover_fee) > 0) ? (
                    <div className="mt-3 text-xs text-muted-foreground">
                      Separately disclosed: late fee {money(record.currency, record.disclosed_late_fee)} · rollover/extension fee {money(record.currency, record.disclosed_rollover_fee)}. These do not silently alter the baseline period-cost metric.
                    </div>
                  ) : null}
                  <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <span>Source: {record.source_provider}</span>
                    {record.source_url ? <a className="inline-flex items-center gap-1 text-primary hover:underline" href={record.source_url} target="_blank" rel="noreferrer">Evidence <ExternalLink size={12} /></a> : null}
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Record pricing observation</CardTitle>
          <CardDescription>
            Enter a representative public offer or documented test result. This creates a new observation; it does not overwrite previous pricing history.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={submit}>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <label className={labelClass}>Tracked app<select className={inputClass} value={appId} onChange={(event) => selectApp(event.target.value)} required><option value="">Select app</option>{apps.map((app) => <option key={app.id} value={app.id}>{app.app_name ?? app.package_name}</option>)}</select></label>
              <label className={labelClass}>Amount received<input className={inputClass} type="number" min="0.01" step="0.01" value={amountReceived} onChange={(event) => setAmountReceived(event.target.value)} required /></label>
              <label className={labelClass}>Total repayment<input className={inputClass} type="number" min="0.01" step="0.01" value={totalRepayment} onChange={(event) => setTotalRepayment(event.target.value)} required /></label>
              <label className={labelClass}>Term days<input className={inputClass} type="number" min="1" step="1" value={termDays} onChange={(event) => setTermDays(event.target.value)} required /></label>
              <label className={labelClass}>Advertised rate %<input className={inputClass} type="number" min="0" step="0.0001" value={advertisedRate} onChange={(event) => setAdvertisedRate(event.target.value)} /></label>
              <label className={labelClass}>Rate basis<select className={inputClass} value={rateBasis} onChange={(event) => setRateBasis(event.target.value as LoanPricingInput["advertised_rate_basis"])}><option value="unspecified">Unspecified</option><option value="daily">Daily</option><option value="weekly">Weekly</option><option value="monthly">Monthly</option><option value="term">Whole term</option><option value="annual">Annual</option></select></label>
              <label className={labelClass}>Interest amount<input className={inputClass} type="number" min="0" step="0.01" value={interestAmount} onChange={(event) => setInterestAmount(event.target.value)} /></label>
              <label className={labelClass}>Processing fee<input className={inputClass} type="number" min="0" step="0.01" value={processingFee} onChange={(event) => setProcessingFee(event.target.value)} /></label>
              <label className={labelClass}>Service fee<input className={inputClass} type="number" min="0" step="0.01" value={serviceFee} onChange={(event) => setServiceFee(event.target.value)} /></label>
              <label className={labelClass}>Insurance fee<input className={inputClass} type="number" min="0" step="0.01" value={insuranceFee} onChange={(event) => setInsuranceFee(event.target.value)} /></label>
              <label className={labelClass}>Disbursement fee<input className={inputClass} type="number" min="0" step="0.01" value={disbursementFee} onChange={(event) => setDisbursementFee(event.target.value)} /></label>
              <label className={labelClass}>Other mandatory fees<input className={inputClass} type="number" min="0" step="0.01" value={otherFees} onChange={(event) => setOtherFees(event.target.value)} /></label>
              <label className={labelClass}>Disclosed late fee<input className={inputClass} type="number" min="0" step="0.01" value={lateFee} onChange={(event) => setLateFee(event.target.value)} /></label>
              <label className={labelClass}>Rollover / extension fee<input className={inputClass} type="number" min="0" step="0.01" value={rolloverFee} onChange={(event) => setRolloverFee(event.target.value)} /></label>
              <label className={labelClass}>Source label<input className={inputClass} value={sourceProvider} onChange={(event) => setSourceProvider(event.target.value)} required /></label>
              <label className={labelClass}>HTTPS source URL<input className={inputClass} type="url" placeholder="https://provider.example/terms" value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} /></label>
            </div>
            <div className="text-xs text-muted-foreground">Late/default and rollover/extension charges are preserved separately. KDR does not convert this period cost into APR unless a versioned methodology is implemented later.</div>
            <Button type="submit" disabled={saving || !appId || !sourceProvider.trim()}><PlusCircle size={15} />{saving ? "Recording" : "Record observation"}</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
