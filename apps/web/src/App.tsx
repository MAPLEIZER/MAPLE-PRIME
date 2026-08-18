import { RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { loadDashboardSummary, syncAlphaSources } from "@/api/dashboard";
import type { DashboardSummary } from "@/api/dashboard";
import { AppSidebar } from "@/components/AppSidebar";
import { Button } from "@/components/ui/Button";
import { navigationItems } from "@/domain/dashboard";
import type { NavigationId } from "@/domain/dashboard";
import { OverviewPage } from "@/pages/OverviewPage";
import { PlaceholderPage } from "@/pages/PlaceholderPage";

const descriptions: Record<Exclude<NavigationId, "overview">, string> = {
  institutions: "Search regulator-backed institution records, aliases and provenance.",
  requests: "Track targeted data-rights requests and their audit timelines.",
  evidence: "Review local evidence and explicitly shared DCP mapping metadata.",
  cases: "Browse verified ODPC determinations and linked court outcomes.",
  reports: "Generate reproducible reconciliation and rights-workflow exports.",
};

export function App() {
  const [active, setActive] = useState<NavigationId>("overview");
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [summaryError, setSummaryError] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);
  const current = navigationItems.find((item) => item.id === active) ?? navigationItems[0];

  useEffect(() => {
    const controller = new AbortController();
    loadDashboardSummary(controller.signal)
      .then((value) => {
        setSummary(value);
        setSummaryError(false);
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setSummaryError(true);
      });
    return () => controller.abort();
  }, []);

  async function handleSync() {
    setSyncing(true);
    setSyncError(null);
    try {
      const failures = await syncAlphaSources();
      try {
        setSummary(await loadDashboardSummary());
        setSummaryError(false);
      } catch {
        setSummaryError(true);
      }
      if (failures.length > 0) {
        setSyncError(`Sync failed for: ${failures.join(", ")}`);
      }
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground md:flex">
      <AppSidebar active={active} onNavigate={setActive} />
      <main className="min-w-0 flex-1">
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-border bg-card px-5 py-4 md:px-8">
          <div>
            <p className="m-0 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Regulatory intelligence</p>
            <h1 className="mb-0 mt-1 text-xl font-semibold tracking-tight">{current.label}</h1>
          </div>
          <div className="flex items-center gap-3">
            {syncError ? <span className="max-w-64 text-right text-xs text-destructive">{syncError}</span> : null}
            <Button className="bg-card text-foreground" disabled={syncing} onClick={handleSync}>
              <RefreshCw size={15} className={syncing ? "animate-spin" : undefined} />
              {syncing ? "Syncing" : "Sync sources"}
            </Button>
          </div>
        </header>
        <div className="p-5 md:p-8">
          {active === "overview" ? (
            <OverviewPage summary={summary} unavailable={summaryError} />
          ) : (
            <PlaceholderPage title={current.label} description={descriptions[active]} />
          )}
        </div>
      </main>
    </div>
  );
}
