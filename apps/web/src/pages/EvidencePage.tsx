import { ExternalLink, FileCheck2, KeyRound, Search, ShieldCheck, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { loadPlayDiscoveryStatus, runPlayDiscovery } from "@/api/apps";
import type { PlayDiscoveryStatus } from "@/api/apps";
import {
  loadBRSEvidence,
  reviewBRSEvidence,
  uploadBRSEvidence,
} from "@/api/evidence";
import type { BRSEvidenceDocument } from "@/api/evidence";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";

export function EvidencePage() {
  const [documents, setDocuments] = useState<BRSEvidenceDocument[]>([]);
  const [discoveryStatus, setDiscoveryStatus] = useState<PlayDiscoveryStatus | null>(null);
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
      setDiscoveryStatus(await loadPlayDiscoveryStatus());
    } catch {
      setDiscoveryStatus(null);
    }
  }

  useEffect(() => {
    void refreshDocuments();
    void refreshDiscoveryStatus();
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
      await refreshDiscoveryStatus();
    } catch (caught) {
      setError(caught instanceof Error
        ? caught.message
        : "Google Play discovery could not complete.");
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

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Google Play → CBK discovery</CardTitle>
          <CardDescription>
            Use the latest persisted CBK DCP identities as search seeds, collect public Google Play metadata, append observations, score ownership candidates and mirror them into the typed relationship evidence graph.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <Button disabled={discovering} onClick={() => void discover()}>
              <Search size={15} />{discovering ? "Discovering" : "Run discovery now"}
            </Button>
            <Badge>{discoveryStatus?.active_provider ?? "provider status unavailable"}</Badge>
            <div className="text-xs text-muted-foreground">
              Manual runs are intentionally small (5 CBK providers / 15 app identities) so the local API stays responsive. SerpApi search rows are retained even if product-detail enrichment is unavailable or quota-limited.
            </div>
          </div>

          <div className="rounded-lg border border-border bg-muted/20 p-4 text-sm">
            <div className="flex items-center gap-2 font-medium"><KeyRound size={15} />Recommended indexed provider: SerpApi</div>
            <div className="mt-2 text-xs leading-5 text-muted-foreground">
              SerpApi exposes structured Google Play search results and product metadata, including developer contact fields. To connect it, add
              <code className="mx-1">KDR_PLAY_DISCOVERY_PROVIDER=serpapi</code> and
              <code className="mx-1">KDR_SERPAPI_API_KEY=&lt;your-key&gt;</code> to
              <code className="mx-1">.kdr/runtime.env</code>, then choose <strong>Repair / rebuild</strong> in the installer. The key stays in your local runtime file and is never written into KDR evidence records.
            </div>
            <div className="mt-2 text-xs text-muted-foreground">
              {discoveryStatus?.serpapi_key_configured
                ? "SerpApi key detected. Indexed discovery is ready."
                : "No SerpApi key detected; KDR will use the public Play HTML fallback and will stop rather than bypass Play anti-bot controls."}
            </div>
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
