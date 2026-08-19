import { ExternalLink, FileCheck2, KeyRound, Search, ShieldCheck, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import {
  loadPlayDiscoveryStatus,
  loadSerpApiAccountHealth,
  runPlayDiscovery,
} from "@/api/apps";
import type { PlayDiscoveryStatus, SerpApiAccountHealth } from "@/api/apps";
import {
  loadBRSEvidence,
  reviewBRSEvidence,
  uploadBRSEvidence,
} from "@/api/evidence";
import type { BRSEvidenceDocument } from "@/api/evidence";
import { PlayResearchConsole } from "@/components/PlayResearchConsole";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";

function accountSummary(account: SerpApiAccountHealth): string {
  if (!account.checked) return account.error ?? "SerpApi.com Account API was not checked.";
  if (account.key_valid === false) return account.error ?? "SerpApi.com reports that the configured API key is invalid.";
  if (account.error) return account.error;

  const parts = [account.account_status, account.plan_name].filter(Boolean);
  if (account.searches_left !== null) parts.push(`${account.searches_left} searches left`);
  if (account.this_hour_searches !== null && account.hourly_limit !== null) {
    parts.push(`${account.this_hour_searches}/${account.hourly_limit} searches this hour`);
  }
  if (account.plan_renewal_date) parts.push(`renews ${account.plan_renewal_date}`);
  return parts.join(" · ") || "SerpApi.com account is reachable.";
}

export function EvidencePage() {
  const [documents, setDocuments] = useState<BRSEvidenceDocument[]>([]);
  const [discoveryStatus, setDiscoveryStatus] = useState<PlayDiscoveryStatus | null>(null);
  const [accountHealth, setAccountHealth] = useState<SerpApiAccountHealth | null>(null);
  const [checkingAccount, setCheckingAccount] = useState(false);
  const [documentType, setDocumentType] = useState<BRSEvidenceDocument["document_type"]>("brs_cr12");
  const [discovering, setDiscovering] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [workingId, setWorkingId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [discoveryWarnings, setDiscoveryWarnings] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  async function refreshDocuments() {
    try {
      setDocuments(await loadBRSEvidence());
    } catch {
      setError("Stored BRS evidence could not be loaded.");
    }
  }

  async function refreshDiscoveryStatus() {
    try {
      const status = await loadPlayDiscoveryStatus();
      setDiscoveryStatus(status);
      if (status.active_provider !== "serpapi") setAccountHealth(null);
      return status;
    } catch {
      setDiscoveryStatus(null);
      return null;
    }
  }

  async function refreshAccountHealth() {
    setCheckingAccount(true);
    try {
      setAccountHealth(await loadSerpApiAccountHealth());
    } catch {
      setAccountHealth({
        checked: false,
        key_valid: null,
        account_status: null,
        plan_name: null,
        searches_left: null,
        this_month_usage: null,
        this_hour_searches: null,
        hourly_limit: null,
        plan_renewal_date: null,
        error: "SerpApi.com Account API health check could not be loaded.",
      });
    } finally {
      setCheckingAccount(false);
    }
  }

  useEffect(() => {
    void refreshDocuments();
    void (async () => {
      const status = await refreshDiscoveryStatus();
      if (status?.active_provider === "serpapi") await refreshAccountHealth();
    })();
  }, []);

  async function discover() {
    setDiscovering(true);
    setNotice(null);
    setDiscoveryWarnings([]);
    setError(null);
    try {
      const result = await runPlayDiscovery();
      setDiscoveryWarnings(result.failures);
      setNotice(
        `${result.provider} · ${result.search_requests} search requests · ${result.detail_requests} product lookups · ${result.apps_ingested} apps ingested · ${result.ownership_candidates} ownership candidates · ${result.relationship_edges} typed relationship edges`,
      );
      const status = await refreshDiscoveryStatus();
      if (status?.active_provider === "serpapi") await refreshAccountHealth();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Google Play discovery could not complete.");
      if (discoveryStatus?.active_provider === "serpapi") await refreshAccountHealth();
    } finally {
      setDiscovering(false);
    }
  }

  async function upload(file: File) {
    setUploading(true);
    setNotice(null);
    setError(null);
    try {
      if (file.type !== "application/pdf") throw new Error("Choose a PDF output from BRS.");
      if (file.size > 10 * 1024 * 1024) throw new Error("BRS PDF exceeds the 10 MB local limit.");
      const document = await uploadBRSEvidence(file, documentType);
      setNotice(`Stored BRS evidence ${document.sha256.slice(0, 12)}… as immutable local evidence.`);
      await refreshDocuments();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "BRS evidence upload failed.");
    } finally {
      setUploading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function review(documentId: string, decision: "manual_verified" | "rejected") {
    setWorkingId(documentId);
    setError(null);
    try {
      await reviewBRSEvidence(documentId, decision);
      await refreshDocuments();
    } catch {
      setError("The BRS evidence verification decision could not be saved.");
    } finally {
      setWorkingId(null);
    }
  }

  const accountLooksHealthy = accountHealth?.key_valid === true
    && (!accountHealth.account_status || accountHealth.account_status.toLowerCase() === "active")
    && accountHealth.searches_left !== 0
    && !accountHealth.error;
  const activeProvider = discoveryStatus?.active_provider ?? "provider status unavailable";

  return (
    <div className="space-y-6">
      <PlayResearchConsole />

      <Card>
        <CardHeader>
          <CardTitle>Provider health & legacy CBK-seeded discovery</CardTitle>
          <CardDescription>
            Keep the original small CBK-name search for quick ownership-oriented checks. For large Finance enumeration, query sweeps, dedupe and CSV review, use the research console above.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <Button disabled={discovering} onClick={() => void discover()}>
              <Search size={15} />{discovering ? "Discovering" : "Run small CBK-seeded discovery"}
            </Button>
            <Badge>{activeProvider}</Badge>
            <div className="text-xs text-muted-foreground">
              This compatibility run remains intentionally small (5 CBK providers / 15 app identities). The research console can enumerate up to 500 unique app identities with a configurable request/enrichment budget.
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-lg border border-border bg-muted/20 p-4 text-sm">
              <div className="flex items-center gap-2 font-medium"><KeyRound size={15} />TalorData</div>
              <div className="mt-2 text-xs leading-5 text-muted-foreground">
                Uses TalorData&apos;s Bearer-token SERP endpoint. Configure
                <code className="mx-1">KDR_PLAY_DISCOVERY_PROVIDER=talordata</code> and
                <code className="mx-1">KDR_TALORDATA_API_KEY=&lt;SERP-token&gt;</code>, then Repair / rebuild.
              </div>
              <div className="mt-2 text-xs text-muted-foreground">
                {discoveryStatus?.talordata_key_configured ? "TalorData token detected in local runtime." : "No TalorData token detected."}
              </div>
            </div>

            <div className="rounded-lg border border-border bg-muted/20 p-4 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2 font-medium"><KeyRound size={15} />SerpApi.com</div>
                {activeProvider === "serpapi" ? (
                  <Button className="h-8 bg-card px-3 text-xs text-foreground" disabled={checkingAccount} onClick={() => void refreshAccountHealth()}>
                    {checkingAccount ? "Checking account" : "Re-check account"}
                  </Button>
                ) : null}
              </div>
              <div className="mt-2 text-xs leading-5 text-muted-foreground">
                Configure <code className="mx-1">KDR_PLAY_DISCOVERY_PROVIDER=serpapi</code> and
                <code className="mx-1">KDR_SERPAPI_API_KEY=&lt;your-key&gt;</code>. KDR keeps keyword and Finance-category searches as separate Google Play request modes.
              </div>
              <div className="mt-2 text-xs text-muted-foreground">
                {discoveryStatus?.serpapi_key_configured ? "SerpApi.com key detected in local runtime." : "No SerpApi.com key detected."}
              </div>
              {activeProvider === "serpapi" ? (
                <div className={`mt-3 rounded-md border p-3 text-xs ${accountLooksHealthy ? "border-emerald-500/30 bg-emerald-500/5" : "border-amber-500/30 bg-amber-500/5"}`}>
                  <div className="font-medium">SerpApi.com account health</div>
                  <div className="mt-1 text-muted-foreground">
                    {checkingAccount && !accountHealth ? "Checking the free Account API…" : accountHealth ? accountSummary(accountHealth) : "Account health has not been checked yet."}
                  </div>
                  <div className="mt-1 text-muted-foreground">The Account API check is diagnostic only and does not consume a search credit.</div>
                </div>
              ) : null}
            </div>
          </div>

          <div className="rounded-lg border border-border p-3 text-xs text-muted-foreground">
            Set <code>KDR_PLAY_DISCOVERY_PROVIDER=auto</code> to prefer TalorData when configured, then SerpApi.com, then the bounded public-HTML fallback. Provider credentials stay local and are never written into evidence records.
            {discoveryStatus?.configuration_note ? <div className="mt-2 text-amber-600">{discoveryStatus.configuration_note}</div> : null}
          </div>

          {notice ? <div className="text-sm text-primary">{notice}</div> : null}
          {discoveryWarnings.length > 0 ? (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-xs">
              <div className="font-medium">Discovery completed with {discoveryWarnings.length} warning{discoveryWarnings.length === 1 ? "" : "s"}</div>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-muted-foreground">
                {discoveryWarnings.map((warning) => <li key={warning}>{warning}</li>)}
              </ul>
            </div>
          ) : null}
          {error ? <div className="text-sm text-destructive">{error}</div> : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>BRS corporate evidence</CardTitle>
          <CardDescription>
            BRS Official company search is a paid service, so a researcher can buy the official search themselves, download the output and upload it here. The alpha preserves the PDF by SHA-256 and extracts only company/document identifiers into searchable fields by default.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 lg:grid-cols-[220px_auto_1fr] lg:items-center">
            <select
              className="h-10 rounded-md border border-border bg-background px-3 text-sm"
              value={documentType}
              onChange={(event) => setDocumentType(event.target.value as BRSEvidenceDocument["document_type"])}
              aria-label="BRS document type"
            >
              <option value="brs_cr12">Company official search / CR12</option>
              <option value="brs_beneficial_ownership_search">Beneficial ownership official search</option>
            </select>
            <input
              ref={fileInput}
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void upload(file);
              }}
            />
            <Button disabled={uploading} onClick={() => fileInput.current?.click()}>
              <Upload size={15} />{uploading ? "Uploading" : "Upload BRS PDF"}
            </Button>
            <div className="text-xs text-muted-foreground">Maximum 10 MB. Natural-person beneficial-owner details remain inside the local source PDF unless a later privacy-reviewed workflow explicitly needs them.</div>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <a className="rounded-lg border border-border p-3 text-sm hover:bg-muted/40" href="https://brsv2.ecitizen.go.ke/" target="_blank" rel="noreferrer">
              <div className="font-medium">Official company search <ExternalLink size={13} className="ml-1 inline" /></div>
              <div className="mt-1 text-xs text-muted-foreground">Purchase/download BRS outputs yourself.</div>
            </a>
            <a className="rounded-lg border border-border p-3 text-sm hover:bg-muted/40" href="https://brs.go.ke/forms/" target="_blank" rel="noreferrer">
              <div className="font-medium">Beneficial ownership LBOF6 <ExternalLink size={13} className="ml-1 inline" /></div>
              <div className="mt-1 text-xs text-muted-foreground">BRS publishes the official-search request form.</div>
            </a>
            <a className="rounded-lg border border-border p-3 text-sm hover:bg-muted/40" href="https://manual.brs.go.ke/verify" target="_blank" rel="noreferrer">
              <div className="font-medium">Verify BRS output <ExternalLink size={13} className="ml-1 inline" /></div>
              <div className="mt-1 text-xs text-muted-foreground">The public checker requires the application number and a security-question answer, so KDR does not falsely claim unattended API verification.</div>
            </a>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Uploaded BRS evidence</CardTitle>
          <CardDescription>Verification changes KDR&apos;s review state, never the stored document bytes or SHA-256 identity.</CardDescription>
        </CardHeader>
        <CardContent>
          {documents.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border p-7 text-center text-sm text-muted-foreground">No BRS evidence documents have been uploaded yet.</div>
          ) : (
            <div className="space-y-3">
              {documents.map((document) => (
                <div key={document.id} className="rounded-lg border border-border p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2"><FileCheck2 size={16} /><span className="font-medium">{document.company_name ?? "BRS document — company name not extracted"}</span></div>
                      <div className="mt-1 text-xs text-muted-foreground">{document.registration_number ?? "Registration number not extracted"} · {document.page_count} pages · SHA-256 {document.sha256.slice(0, 16)}…</div>
                      {document.application_number ? <div className="mt-1 text-xs text-muted-foreground">Application: {document.application_number}</div> : null}
                    </div>
                    <Badge>{document.verification_state}</Badge>
                  </div>
                  {document.verification_state === "uploaded_unverified" ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Button disabled={workingId === document.id} onClick={() => void review(document.id, "manual_verified")}><ShieldCheck size={14} />I verified this on BRS</Button>
                      <Button className="bg-card text-foreground" disabled={workingId === document.id} onClick={() => void review(document.id, "rejected")}>Reject document</Button>
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
