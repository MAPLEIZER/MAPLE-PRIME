import { RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { loadDashboardSummary } from "@/api/dashboard";
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

  return (
    <div className="min-h-screen bg-background text-foreground md:flex">
      <AppSidebar active={active} onNavigate={setActive} />
      <main className="min-w-0 flex-1">
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-border bg-card px-5 py-4 md:px-8">
          <div>
            <p className="m-0 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Regulatory intelligence</p>
            <h1 className="mb-0 mt-1 text-xl font-semibold tracking-tight">{current.label}</h1>
          </div>
          <Button className="bg-card text-foreground" disabled>
            <RefreshCw size={15} /> Sync sources
          </Button>
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
