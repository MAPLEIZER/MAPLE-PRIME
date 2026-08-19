import { RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import {
  loadDashboardSummary,
  loadReconciliationFindings,
  reviewFinding,
  syncAlphaSources,
} from "@/api/dashboard";
import type {
  DashboardSummary,
  ReconciliationFinding,
  SyncStageEvent,
} from "@/api/dashboard";
import {
  discoverConsultations,
  draftConsultation,
  loadConsultations,
  loadLegalLibrary,
} from "@/api/knowledge";
import type { CivicCandidate, Consultation, LegalEntry } from "@/api/knowledge";
import { AppSidebar } from "@/components/AppSidebar";
import { Button } from "@/components/ui/Button";
import { navigationItems } from "@/domain/dashboard";
import type { NavigationId } from "@/domain/dashboard";
import { CivicParticipationPage } from "@/pages/CivicParticipationPage";
import { LegalLibraryPage } from "@/pages/LegalLibraryPage";
import { LoanAppsPage } from "@/pages/LoanAppsPage";
import { OverviewPage } from "@/pages/OverviewPage";
import { PlaceholderPage } from "@/pages/PlaceholderPage";
import { ReportsPage } from "@/pages/ReportsPage";

const descriptions: Record<Exclude<NavigationId, "overview" | "loan_apps" | "reports" | "legal" | "civic">, string> = {
  institutions: "Search regulator-backed institution records, aliases and provenance.",
  requests: "Track targeted data-rights requests and their audit timelines.",
  evidence: "Review local evidence and explicitly shared DCP mapping metadata.",
  cases: "Browse verified ODPC determinations and linked court outcomes.",
};

export function App() {
  const [active, setActive] = useState<NavigationId>("overview");
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [summaryError, setSummaryError] = useState(false);
  const [findings, setFindings] = useState<ReconciliationFinding[]>([]);
  const [findingsError, setFindingsError] = useState(false);
  const [legalEntries, setLegalEntries] = useState<LegalEntry[]>([]);
  const [legalError, setLegalError] = useState(false);
  const [consultations, setConsultations] = useState<Consultation[]>([]);
  const [civicCandidates, setCivicCandidates] = useState<CivicCandidate[]>([]);
  const [civicError, setCivicError] = useState(false);
  const [discovering, setDiscovering] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncStage, setSyncStage] = useState<SyncStageEvent | null>(null);
  const [syncNotice, setSyncNotice] = useState<string | null>(null);
  const [reviewingId, setReviewingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const current = navigationItems.find((item) => item.id === active) ?? navigationItems[0];

  useEffect(() => {
    const controller = new AbortController();
    loadDashboardSummary(controller.signal).then((value) => { setSummary(value); setSummaryError(false); }).catch((error: unknown) => {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setSummaryError(true);
    });
    loadReconciliationFindings(controller.signal).then((value) => { setFindings(value); setFindingsError(false); }).catch((error: unknown) => {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setFindingsError(true);
    });
    loadLegalLibrary(controller.signal).then((value) => { setLegalEntries(value); setLegalError(false); }).catch((error: unknown) => {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setLegalError(true);
    });
    loadConsultations(controller.signal).then((value) => { setConsultations(value); setCivicError(false); }).catch((error: unknown) => {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setCivicError(true);
    });
    return () => controller.abort();
  }, []);

  async function refreshLocalState() {
    try { setSummary(await loadDashboardSummary()); setSummaryError(false); } catch { setSummaryError(true); }
    try { setFindings(await loadReconciliationFindings()); setFindingsError(false); } catch { setFindingsError(true); }
  }

  async function handleSync() {
    setSyncing(true);
    setSyncStage(null);
    setSyncNotice(null);
    setActionError(null);
    try {
      const report = await syncAlphaSources(setSyncStage);
      await refreshLocalState();
      if (report.failures.length > 0) {
        const completed = report.succeeded.length > 0
          ? `Completed: ${report.succeeded.join(", ")}. `
          : "";
        setActionError(completed + report.failures.map((failure) => `${failure.stage}: ${failure.message}`).join(" "));
      } else {
        setSyncNotice("CBK, ODPC and reconciliation completed successfully.");
      }
    } finally {
      setSyncing(false);
    }
  }

  async function handleDiscover() {
    setDiscovering(true);
    setActionError(null);
    try {
      setCivicCandidates(await discoverConsultations());
    } catch {
      setActionError("Official consultation discovery could not complete. Nothing was submitted.");
    } finally {
      setDiscovering(false);
    }
  }

  async function handleReview(findingId: string, decision: "confirmed" | "rejected") {
    setReviewingId(findingId);
    setActionError(null);
    try {
      await reviewFinding(findingId, decision);
      await refreshLocalState();
    } catch {
      setActionError("Manual review could not be saved.");
    } finally {
      setReviewingId(null);
    }
  }

  let content;
  if (active === "overview") {
    content = <OverviewPage summary={summary} unavailable={summaryError} />;
  } else if (active === "loan_apps") {
    content = <LoanAppsPage />;
  } else if (active === "reports") {
    content = <ReportsPage findings={findings} unavailable={findingsError} reviewingId={reviewingId} onReview={handleReview} />;
  } else if (active === "legal") {
    content = <LegalLibraryPage entries={legalEntries} unavailable={legalError} />;
  } else if (active === "civic") {
    content = (
      <CivicParticipationPage
        consultations={consultations}
        candidates={civicCandidates}
        discovering={discovering}
        unavailable={civicError}
        onDiscover={handleDiscover}
        onDraft={draftConsultation}
      />
    );
  } else {
    content = <PlaceholderPage title={current.label} description={descriptions[active]} />;
  }

  const syncText = syncing && syncStage
    ? `${syncStage.label}${syncStage.detail ? ` · ${syncStage.detail}` : ""}`
    : syncNotice;

  return (
    <div className="min-h-screen bg-background text-foreground md:flex">
      <AppSidebar active={active} onNavigate={setActive} />
      <main className="min-w-0 flex-1">
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-border bg-card px-5 py-4 md:px-8">
          <div>
            <p className="m-0 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Regulatory intelligence</p>
            <h1 className="mb-0 mt-1 text-xl font-semibold tracking-tight">{current.label}</h1>
          </div>
          <div className="flex max-w-full items-center gap-3">
            <div className="max-w-xl text-right">
              {syncText ? <div className="text-xs text-muted-foreground">{syncText}</div> : null}
              {actionError ? <div className="mt-1 text-xs text-destructive">{actionError}</div> : null}
            </div>
            <Button className="bg-card text-foreground" disabled={syncing} onClick={handleSync}>
              <RefreshCw size={15} className={syncing ? "animate-spin" : undefined} />
              {syncing ? "Syncing" : "Sync sources"}
            </Button>
          </div>
        </header>
        <div className="p-5 md:p-8">{content}</div>
      </main>
    </div>
  );
}
