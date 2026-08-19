import { Database, Download, Mail, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  loadPlayDiscoveryStatus,
  runPlayResearch,
} from "@/api/apps";
import type {
  PlayDiscoveryStatus,
  PlayResearchRequest,
  PlayResearchResult,
  PlayResearchRow,
} from "@/api/apps";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";

const FALLBACK_TERMS = [
  "loan",
  "credit",
  "mkopo",
  "advance",
  "salary advance",
  "cash loan",
  "mobile loan",
  "quick loan",
  "emergency loan",
  "digital credit",
  "microloan",
  "borrow",
  "pesa",
];

function parseQueries(value: string): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const raw of value.split(/[\n,]+/)) {
    const term = raw.trim().replace(/\s+/g, " ");
    const key = term.toLowerCase();
    if (!term || seen.has(key)) continue;
    seen.add(key);
    result.push(term);
    if (result.length >= 20) break;
  }
  return result;
}

function csvCell(value: unknown): string {
  const text = value == null ? "" : String(value);
  return `"${text.replaceAll('"', '""')}"`;
}

function exportResearchCsv(result: PlayResearchResult, rows = result.results, suffix = "all") {
  const header = [
    "package_name",
    "app_name",
    "developer_name",
    "support_email",
    "developer_website",
    "database_status",
    "email_status",
    "matched_by",
    "installs",
    "store_url",
  ];
  const lines = [header.map(csvCell).join(",")];
  for (const row of rows) {
    lines.push([
      row.package_name,
      row.app_name,
      row.developer_name,
      row.support_email,
      row.developer_website,
      row.database_status,
      row.email_status,
      row.matched_by.join(" | "),
      row.installs,
      row.store_url,
    ].map(csvCell).join(","));
  }
  const blob = new Blob([`${lines.join("\n")}\n`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `kdr-play-research-${suffix}-${new Date().toISOString().replaceAll(":", "-")}.csv`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function ResultBadge({ row }: { row: PlayResearchRow }) {
  if (row.database_status === "new") return <Badge>new app</Badge>;
  if (row.database_status === "enriched") return <Badge>contact enriched</Badge>;
  if (row.database_status === "refreshed") return <Badge>refreshed</Badge>;
  return <Badge>already in DB</Badge>;
}

export function PlayResearchConsole() {
  const [status, setStatus] = useState<PlayDiscoveryStatus | null>(null);
  const [provider, setProvider] = useState<PlayResearchRequest["provider"]>("auto");
  const [mode, setMode] = useState<PlayResearchRequest["mode"]>("category");
  const [queryText, setQueryText] = useState("loan, credit, mkopo, advance, salary advance, mobile loan");
  const [maxPages, setMaxPages] = useState(8);
  const [maxApps, setMaxApps] = useState(300);
  const [enrichLimit, setEnrichLimit] = useState(15);
  const [skipExisting, setSkipExisting] = useState(true);
  const [matchOwnership, setMatchOwnership] = useState(false);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<PlayResearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "new" | "existing" | "email" | "new_email">("all");

  useEffect(() => {
    void (async () => {
      try {
        const next = await loadPlayDiscoveryStatus();
        setStatus(next);
        if (next.active_provider === "serpapi" || next.active_provider === "talordata") {
          setProvider(next.active_provider);
        }
      } catch {
        setStatus(null);
      }
    })();
  }, []);

  const suggestions = status?.suggested_queries?.length ? status.suggested_queries : FALLBACK_TERMS;
  const queries = useMemo(() => parseQueries(queryText), [queryText]);
  const estimatedCalls = maxPages + (provider === "serpapi" || provider === "auto" ? enrichLimit : 0);
  const filteredRows = useMemo(() => {
    const rows = result?.results ?? [];
    if (filter === "new") return rows.filter((row) => row.database_status === "new");
    if (filter === "existing") return rows.filter((row) => row.database_status !== "new");
    if (filter === "email") return rows.filter((row) => Boolean(row.support_email));
    if (filter === "new_email") return rows.filter((row) => row.email_status === "new");
    return rows;
  }, [filter, result]);

  function addSuggestedQuery(term: string) {
    const current = parseQueries(queryText);
    if (current.some((item) => item.toLowerCase() === term.toLowerCase())) return;
    setQueryText([...current, term].join(", "));
  }

  async function run() {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const response = await runPlayResearch({
        provider,
        mode,
        queries,
        max_pages: maxPages,
        max_apps: maxApps,
        enrich_limit: enrichLimit,
        skip_existing: skipExisting,
        match_ownership: matchOwnership,
      });
      setResult(response);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Google Play research could not complete.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Google Play research console</CardTitle>
        <CardDescription>
          Crawl the Kenya-localized Finance category, sweep your own lending keywords, or combine both. Package IDs are deduplicated before ingest; existing apps with known contacts are skipped by default, while reused support emails are flagged instead of silently creating duplicate research work.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
          <label className="space-y-1 text-xs text-muted-foreground">
            <span>Provider</span>
            <select className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground" value={provider} onChange={(event) => setProvider(event.target.value as PlayResearchRequest["provider"])}>
              <option value="auto">Auto</option>
              <option value="serpapi">SerpApi.com</option>
              <option value="talordata">TalorData</option>
            </select>
          </label>
          <label className="space-y-1 text-xs text-muted-foreground">
            <span>Discovery mode</span>
            <select className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground" value={mode} onChange={(event) => setMode(event.target.value as PlayResearchRequest["mode"])}>
              <option value="category">Finance category crawl</option>
              <option value="query">Query sweep</option>
              <option value="hybrid">Category + queries</option>
            </select>
          </label>
          <label className="space-y-1 text-xs text-muted-foreground">
            <span>Search pages / requests</span>
            <input className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground" type="number" min={1} max={25} value={maxPages} onChange={(event) => setMaxPages(Math.max(1, Math.min(25, Number(event.target.value) || 1)))} />
          </label>
          <label className="space-y-1 text-xs text-muted-foreground">
            <span>Maximum app identities</span>
            <input className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground" type="number" min={1} max={500} value={maxApps} onChange={(event) => setMaxApps(Math.max(1, Math.min(500, Number(event.target.value) || 1)))} />
          </label>
          <label className="space-y-1 text-xs text-muted-foreground">
            <span>SerpApi email enrichments</span>
            <input className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground" type="number" min={0} max={100} value={enrichLimit} onChange={(event) => setEnrichLimit(Math.max(0, Math.min(100, Number(event.target.value) || 0)))} />
          </label>
          <div className="space-y-1 text-xs text-muted-foreground">
            <span>Request budget</span>
            <div className="flex h-10 items-center rounded-md border border-border bg-muted/20 px-3 text-sm text-foreground">≤ {estimatedCalls} provider calls</div>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
          <div className="space-y-2">
            <label className="text-xs font-medium">Query terms</label>
            <textarea
              className="min-h-24 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground"
              value={queryText}
              onChange={(event) => setQueryText(event.target.value)}
              placeholder="loan, credit, mkopo, advance, salary advance…"
            />
            <div className="text-xs text-muted-foreground">
              Used in Query sweep and Hybrid modes. Separate terms with commas or new lines; up to 20 unique terms are sent.
            </div>
            <div className="flex flex-wrap gap-2">
              {suggestions.map((term) => (
                <button key={term} type="button" className="rounded-full border border-border bg-muted/20 px-2.5 py-1 text-xs hover:bg-muted/50" onClick={() => addSuggestedQuery(term)}>
                  + {term}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-3 rounded-lg border border-border bg-muted/20 p-4 text-xs">
            <label className="flex items-start gap-2">
              <input type="checkbox" checked={skipExisting} onChange={(event) => setSkipExisting(event.target.checked)} />
              <span><strong>Skip apps already complete in KDR.</strong> Existing packages with a saved support email are not reparsed. Existing packages still missing an email remain eligible for the optional enrichment budget.</span>
            </label>
            <label className="flex items-start gap-2">
              <input type="checkbox" checked={matchOwnership} onChange={(event) => setMatchOwnership(event.target.checked)} />
              <span><strong>Run CBK ownership matching.</strong> Leave off for large enumeration passes; turn on when you want candidate links generated immediately.</span>
            </label>
            <div className="text-muted-foreground">
              Category crawl follows the provider&apos;s discoverable/ranked Finance pages. It improves coverage substantially, but it is not represented as a guaranteed canonical list of every app Google has ever classified as Finance.
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Button disabled={running} onClick={() => void run()}>
            <Search size={15} />{running ? "Researching…" : "Run research"}
          </Button>
          <Badge>{provider}</Badge>
          <span className="text-xs text-muted-foreground">
            SerpApi configured: {status?.serpapi_key_configured ? "yes" : "no"} · TalorData configured: {status?.talordata_key_configured ? "yes" : "no"}
          </span>
          {result ? <Button className="bg-card text-foreground" onClick={() => exportResearchCsv(result)}><Download size={14} />Export all CSV</Button> : null}
          {result?.new_unique_emails ? (
            <Button className="bg-card text-foreground" onClick={() => exportResearchCsv(result, result.results.filter((row) => row.email_status === "new"), "new-emails")}>
              <Mail size={14} />Export new emails
            </Button>
          ) : null}
        </div>

        {error ? <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">{error}</div> : null}

        {result ? (
          <>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
              <div className="rounded-lg border border-border p-3"><div className="text-xs text-muted-foreground">Unique apps</div><div className="mt-1 text-xl font-semibold">{result.unique_apps_discovered}</div></div>
              <div className="rounded-lg border border-border p-3"><div className="text-xs text-muted-foreground">New to KDR</div><div className="mt-1 text-xl font-semibold">{result.new_apps}</div></div>
              <div className="rounded-lg border border-border p-3"><div className="text-xs text-muted-foreground">Already known</div><div className="mt-1 text-xl font-semibold">{result.existing_apps}</div><div className="mt-1 text-[11px] text-muted-foreground">{result.enriched_existing_apps} contact-enriched this run</div></div>
              <div className="rounded-lg border border-border p-3"><div className="flex items-center gap-1 text-xs text-muted-foreground"><Mail size={13} />Emails visible</div><div className="mt-1 text-xl font-semibold">{result.emails_found}</div></div>
              <div className="rounded-lg border border-border p-3"><div className="text-xs text-muted-foreground">New unique emails</div><div className="mt-1 text-xl font-semibold">{result.new_unique_emails}</div></div>
              <div className="rounded-lg border border-border p-3"><div className="flex items-center gap-1 text-xs text-muted-foreground"><Database size={13} />API calls</div><div className="mt-1 text-xl font-semibold">{result.search_requests + result.detail_requests}</div></div>
            </div>

            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="text-muted-foreground">Show:</span>
              {(["all", "new", "existing", "email", "new_email"] as const).map((value) => (
                <button key={value} type="button" className={`rounded-md border px-2.5 py-1 ${filter === value ? "bg-primary text-primary-foreground" : "border-border bg-card"}`} onClick={() => setFilter(value)}>
                  {value === "all" ? "All" : value === "new" ? "New apps" : value === "existing" ? "Already known" : value === "email" ? "Has email" : "New emails only"}
                </button>
              ))}
              <span className="ml-auto text-muted-foreground">
                {result.pages_fetched} pages fetched · {result.duplicate_packages_skipped} duplicate package hits skipped · {result.existing_email_hits} existing email hits · {result.duplicate_emails_in_run} repeated new-email hits
              </span>
            </div>

            <div className="overflow-x-auto rounded-lg border border-border">
              <table className="w-full min-w-[980px] text-left text-xs">
                <thead className="bg-muted/40 text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2">App</th>
                    <th className="px-3 py-2">Developer</th>
                    <th className="px-3 py-2">Support email</th>
                    <th className="px-3 py-2">Database</th>
                    <th className="px-3 py-2">Found through</th>
                    <th className="px-3 py-2">Play</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRows.map((row) => (
                    <tr key={row.package_name} className="border-t border-border align-top">
                      <td className="px-3 py-3">
                        <div className="font-medium">{row.app_name}</div>
                        <div className="mt-1 font-mono text-[11px] text-muted-foreground">{row.package_name}</div>
                      </td>
                      <td className="px-3 py-3">{row.developer_name}</td>
                      <td className="px-3 py-3">
                        {row.support_email ? <div>{row.support_email}</div> : <span className="text-muted-foreground">not enriched</span>}
                        {row.email_status !== "none" ? <div className="mt-1 text-[11px] text-muted-foreground">{row.email_status.replaceAll("_", " ")}</div> : null}
                      </td>
                      <td className="px-3 py-3"><ResultBadge row={row} /></td>
                      <td className="px-3 py-3"><div className="max-w-56 space-y-1">{row.matched_by.map((item) => <div key={item}>{item}</div>)}</div></td>
                      <td className="px-3 py-3"><a className="text-primary hover:underline" href={row.store_url} target="_blank" rel="noreferrer">Open</a></td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filteredRows.length === 0 ? <div className="p-6 text-center text-sm text-muted-foreground">No rows match this filter.</div> : null}
            </div>

            {result.failures.length ? (
              <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-xs">
                <div className="font-medium">Research completed with {result.failures.length} warning{result.failures.length === 1 ? "" : "s"}</div>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-muted-foreground">
                  {result.failures.map((warning) => <li key={warning}>{warning}</li>)}
                </ul>
              </div>
            ) : null}
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}
