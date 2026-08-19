import { BadgeDollarSign, BookOpenText, Building2, Database, FileCheck2, FolderSearch2, Landmark, Scale, Send, Smartphone } from "lucide-react";
import type { SyntheticEvent } from "react";
import type { LucideIcon } from "lucide-react";
import { navigationItems } from "@/domain/dashboard";
import type { NavigationId } from "@/domain/dashboard";

const icons: Record<NavigationId, LucideIcon> = {
  overview: Database,
  institutions: Building2,
  loan_apps: Smartphone,
  pricing: BadgeDollarSign,
  requests: FileCheck2,
  evidence: FolderSearch2,
  cases: Scale,
  reports: Send,
  legal: BookOpenText,
  civic: Landmark,
};

const brandLogo = "./kdr-logo-transparent.png";
const brandIcon = "./kdr-app-icon.png";

function fallBackToIcon(event: SyntheticEvent<HTMLImageElement>) {
  const image = event.currentTarget;
  if (!image.src.endsWith("kdr-app-icon.png")) {
    image.src = brandIcon;
  }
}

interface AppSidebarProps { active: NavigationId; onNavigate: (id: NavigationId) => void }

export function AppSidebar({ active, onNavigate }: AppSidebarProps) {
  return (
    <aside className="flex w-full shrink-0 flex-col border-b border-border bg-card md:min-h-screen md:w-64 md:border-b-0 md:border-r">
      <div className="border-b border-border px-5 py-4 md:py-5">
        <div className="hidden md:block">
          <div className="mx-auto flex min-h-20 items-center justify-center rounded-xl bg-white/95 p-2">
            <img src={brandLogo} onError={fallBackToIcon} alt="Kenya Data Rights" className="max-h-20 w-full object-contain" />
          </div>
          <div className="mt-2 text-center text-xs text-muted-foreground">Local-first privacy control</div>
        </div>
        <div className="flex items-center gap-3 md:hidden">
          <img src={brandIcon} alt="Kenya Data Rights" className="size-10 shrink-0 rounded-xl bg-white object-contain p-1" />
          <div className="min-w-0"><div className="text-sm font-semibold">Kenya Data Rights</div><div className="text-xs text-muted-foreground">Local-first privacy control</div></div>
        </div>
      </div>
      <nav aria-label="Primary" className="grid grid-cols-2 gap-1 p-3 md:grid-cols-1">
        {navigationItems.map((item) => {
          const Icon = icons[item.id];
          const selected = item.id === active;
          return (
            <button key={item.id} type="button" onClick={() => onNavigate(item.id)} className={`flex min-h-10 items-center gap-2 rounded-md px-3 text-left text-sm transition-colors ${selected ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"}`}>
              <Icon size={16} aria-hidden="true" /><span>{item.label}</span>
            </button>
          );
        })}
      </nav>
      <div className="mt-auto hidden border-t border-border p-4 text-xs text-muted-foreground md:block">Local-first · telemetry off by default</div>
    </aside>
  );
}
