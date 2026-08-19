import { ExternalLink, Link2, Search, ShieldCheck, Upload } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  importPlayApps,
  loadAppRegistrySummary,
  loadLoanApps,
  reconcileLoanApp,
  reviewAppOwnership,
} from "@/api/apps";
import type { AppRegistrySummary, LoanAppRecord, PlayImportRecord } from "@/api/apps";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";

const inputClass = "h-10 w-full rounded-md border border-border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring";

function confidenceLabel(value: number): string {
  return `${Math.round(value * 100)}% evidence confidence`;
}

function normalizedRecords(payload: unknown): PlayImportRecord[] {
  const records = Array.isArray(payload)
    ? payload
    : payload && typeof payload === "object" && Array.isArray((payload as { records?: unknown }).records)
      ? (payload as { records: unknown[] }).records
      : null;
  if (!records || records.length === 0 || records.length > 500) {
    throw new Error("Expected a normalized JSON batch containing 1–500 records.");
  }
  for (const record of records) {
    if (!record || typeof record !== "object") throw new Error("Each normalized record must be an object.");
    const row = record as Record<string, unknown>;
    for (const required of ["package_name", "app_name", "developer_name", "store_url", "source_provider", "source_url", "observed_at"]) {
      if (typeof row[required] !== "string" || !row[required]) throw new Error(`Normalized record is missing ${required}.`);
    }
  }
  return records as PlayImportRecord[];
}

export function LoanAppsPage() {
  const [apps, setApps] = useState<LoanAppRecord[]>([]);
  const [summary, setSummary] = useState<AppRegistrySummary | null>(null);
  const [query, setQuery] = useState("");
  const [email, setEmail] = useState("");
  const [domain, setDomain] = useState("");
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const [importNotice, setImportNotice] = useState<string | null>(null);
  const [workingId, setWorkingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  async function refresh(filters = { q: query, email, domain }) {
    setLoading(true);
    setError(null);
    try {
      const [records, counts] = await Promise.all([loadLoanApps(filters), loadAppRegistrySummary()]);
      setApps(records);
      setSummary(counts);
    } catch {
      setError("The app identity registry could not be loaded.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void refresh({ q: "", email: "", domain: "" }); }, []);

  const stats = useMemo(() => [
    ["Tracked apps", summary?.apps ?? 0],
    ["Confirmed owner links", summary?.confirmed_ownership_links ?? 0],
    ["Needs review", summary?.candidate_ownership_links ?? 0],
  ] as const, [summary]);

  async function importJson(file: File) {
    setImporting(true);
    setImportNotice(null);
    setError(null);
    try {
      if (file.size > 5 * 1024 * 1024) throw new Error("Import JSON is larger than the 5 MB local safety limit.");
      const payload = JSON.parse(await file.text()) as unknown;
      const records = normalizedRecords(payload);
      const result = await importPlayApps(records);
      setImportNotice(`${result.apps_touched} apps updated · ${result.observations_available} observations available · ${result.ownership_candidates} owner candidates.`);
      setQuery("");
      setEmail("");
      setDomain("");
      await refresh({ q: "", email: "", domain: "" });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The normalized Play JSON could not be imported.");
    } finally {
      setImporting(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function reconcile(appId: string) {
    setWorkingId(appId);
    try {
      await reconcileLoanApp(appId);
      await refresh();
    } catch {
      setError("Ownership candidate generation failed.");
    } finally {
      setWorkingId(null);
    }
  }

  async function review(linkId: string, decision: "confirmed" | "rejected") {
    setWorkingId(linkId);
    try {
      await reviewAppOwnership(linkId, decision);
      await refresh();
    } catch {
      setError("The ownership review could not be saved.");
    } finally {
      setWorkingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-3 md:grid-cols-3">
        {stats.map(([label, value]) => (
          <Card key={label}><CardContent className="pt-5"><div className="text-2xl font-semibold">{value}</div><div className="text-xs text-muted-foreground">{label}</div></CardContent></Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Build the public app registry</CardTitle>
          <CardDescription>
            Import normalized public Google Play metadata from any collector. KDR stores the source and observation time, preserves older observations, then prepares ownership candidates for review. It does not treat a support email or matching domain as proof by itself.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <input
            ref={fileInput}
            type="file"
            accept="application/json,.json"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void importJson(file);
            }}
          />
          <div className="flex flex-wrap items-center gap-3">
            <Button disabled={importing} onClick={() => fileInput.current?.click()}><Upload size={15} />{importing ? "Importing" : "Import normalized JSON"}</Button>
            <div className="text-xs text-muted-foreground">
              Use <code>tools/playstore-import/normalize_export.py</code> for common scraper/API exports. Maximum 500 records / 5 MB per local import.
            </div>
          </div>
          {importNotice ? <div className="text-sm text-primary">{importNotice}</div> : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Loan app identity registry</CardTitle>
          <CardDescription>
            Reverse-search public Play Store support contacts and review evidence linking app packages to regulated or known legal entities. Candidate links are never treated as confirmed ownership until reviewed.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 lg:grid-cols-3">
            <input className={inputClass} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="App, package or developer" aria-label="Search apps" />
            <input className={inputClass} value={email} onChange={(event) => setEmail(event.target.value)} placeholder="support@example.co.ke" aria-label="Reverse lookup by email" />
            <input className={inputClass} value={domain} onChange={(event) => setDomain(event.target.value)} placeholder="example.co.ke" aria-label="Reverse lookup by domain" />
          </div>
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => void refresh()} disabled={loading}><Search size={15} />{loading ? "Searching" : "Search registry"}</Button>
            <Button className="bg-card text-foreground" onClick={() => { setQuery(""); setEmail(""); setDomain(""); void refresh({ q: "", email: "", domain: "" }); }}>Clear</Button>
          </div>
          {error ? <div className="text-sm text-destructive">{error}</div> : null}
        </CardContent>
      </Card>

      <div className="space-y-4">
        {!loading && apps.length === 0 ? <Card><CardContent className="pt-5 text-sm text-muted-foreground">No app records match this lookup yet. Import public Play metadata to grow the registry.</CardContent></Card> : null}
        {apps.map((app) => (
          <Card key={app.id}>
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <CardTitle>{app.app_name ?? app.package_name}</CardTitle>
                  <CardDescription>{app.package_name}</CardDescription>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge>{app.loan_relevance}</Badge>
                  <Badge>{app.source_provider ?? "public source"}</Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 text-sm md:grid-cols-2 xl:grid-cols-4">
                <div><div className="text-xs text-muted-foreground">Developer shown</div><div>{app.developer_name ?? "Not published"}</div></div>
                <div><div className="text-xs text-muted-foreground">Public support email</div><div className="break-all">{app.support_email ?? "Not published"}</div></div>
                <div><div className="text-xs text-muted-foreground">Email / developer domain</div><div className="break-all">{app.email_domain ?? app.developer_domain ?? "Not published"}</div></div>
                <div><div className="text-xs text-muted-foreground">Last observed</div><div>{new Date(app.last_seen_at).toLocaleDateString()}</div></div>
              </div>

              <div className="flex flex-wrap gap-2">
                {app.store_url ? <a className="inline-flex items-center gap-1 text-sm text-primary underline-offset-4 hover:underline" href={app.store_url} target="_blank" rel="noreferrer">Play listing <ExternalLink size={13} /></a> : null}
                {app.developer_website ? <a className="inline-flex items-center gap-1 text-sm text-primary underline-offset-4 hover:underline" href={app.developer_website} target="_blank" rel="noreferrer">Developer site <ExternalLink size={13} /></a> : null}
                {app.source_url ? <a className="inline-flex items-center gap-1 text-sm text-primary underline-offset-4 hover:underline" href={app.source_url} target="_blank" rel="noreferrer">Observation source <ExternalLink size={13} /></a> : null}
              </div>

              <div className="rounded-lg border border-border bg-muted/30 p-4">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2 font-medium"><Link2 size={16} />Owning entity evidence</div>
                  <Button className="bg-card text-foreground" disabled={workingId === app.id} onClick={() => void reconcile(app.id)}>{workingId === app.id ? "Checking" : "Find candidates"}</Button>
                </div>
                {app.ownership_links.length === 0 ? <div className="text-sm text-muted-foreground">No evidence-backed owner candidate has been generated yet.</div> : null}
                <div className="space-y-2">
                  {app.ownership_links.map((link) => (
                    <div key={link.id} className="rounded-md border border-border bg-background p-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>
                          <div className="font-medium">{link.institution_name ?? link.institution_id}</div>
                          <div className="text-xs text-muted-foreground">{confidenceLabel(link.confidence)} · {link.signals.join(", ")}</div>
                        </div>
                        <Badge>{link.review_state}</Badge>
                      </div>
                      {link.review_state === "candidate" ? (
                        <div className="mt-3 flex gap-2">
                          <Button disabled={workingId === link.id} onClick={() => void review(link.id, "confirmed")}><ShieldCheck size={14} />Confirm link</Button>
                          <Button className="bg-card text-foreground" disabled={workingId === link.id} onClick={() => void review(link.id, "rejected")}>Reject</Button>
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
