import { Building2, Database, FileCheck2, FolderSearch2, Scale, Send } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { navigationItems } from "@/domain/dashboard";
import type { NavigationId } from "@/domain/dashboard";

const icons: Record<NavigationId, LucideIcon> = {
  overview: Database,
  institutions: Building2,
  requests: FileCheck2,
  evidence: FolderSearch2,
  cases: Scale,
  reports: Send,
};

interface AppSidebarProps {
  active: NavigationId;
  onNavigate: (id: NavigationId) => void;
}

export function AppSidebar({ active, onNavigate }: AppSidebarProps) {
  return (
    <aside className="flex w-full shrink-0 flex-col border-b border-border bg-card md:min-h-screen md:w-64 md:border-b-0 md:border-r">
      <div className="flex items-center gap-3 border-b border-border px-5 py-5">
        <div className="grid size-9 place-items-center rounded-lg bg-primary text-xs font-bold text-primary-foreground">KDR</div>
        <div className="min-w-0">
          <div className="text-sm font-semibold">Kenya Data Rights</div>
          <div className="text-xs text-muted-foreground">Local-first privacy control</div>
        </div>
      </div>
      <nav aria-label="Primary" className="grid grid-cols-3 gap-1 p-3 md:grid-cols-1">
        {navigationItems.map((item) => {
          const Icon = icons[item.id];
          const selected = item.id === active;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onNavigate(item.id)}
              className={`flex min-h-10 items-center gap-2 rounded-md px-3 text-left text-sm transition-colors ${selected ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"}`}
            >
              <Icon size={16} aria-hidden="true" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
      <div className="mt-auto hidden border-t border-border p-4 text-xs text-muted-foreground md:block">
        Local-first · no telemetry
      </div>
    </aside>
  );
}
