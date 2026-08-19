export type AppOwnershipLink = {
  id: string;
  institution_id: string;
  institution_name: string | null;
  confidence: number;
  signals: string[];
  review_state: "candidate" | "confirmed" | "rejected";
  reviewed_by: string | null;
  reviewed_at: string | null;
};

export type LoanAppRecord = {
  id: string;
  store: string;
  package_name: string;
  loan_relevance: string;
  first_seen_at: string;
  last_seen_at: string;
  app_name: string | null;
  developer_name: string | null;
  developer_id: string | null;
  support_email: string | null;
  email_domain: string | null;
  developer_website: string | null;
  developer_domain: string | null;
  privacy_policy_url: string | null;
  store_url: string | null;
  category: string | null;
  installs: string | null;
  source_provider: string | null;
  source_url: string | null;
  observed_at: string | null;
  ownership_links: AppOwnershipLink[];
};

export type AppRegistrySummary = {
  apps: number;
  confirmed_ownership_links: number;
  candidate_ownership_links: number;
};

export type PlayImportRecord = {
  store?: "google_play";
  package_name: string;
  app_name: string;
  developer_name: string;
  developer_id?: string | null;
  support_email?: string | null;
  developer_website?: string | null;
  privacy_policy_url?: string | null;
  store_url: string;
  category?: string | null;
  installs?: string | null;
  source_provider: string;
  source_url: string;
  observed_at: string;
};

export type PlayImportResult = {
  apps_touched: number;
  observations_available: number;
  ownership_candidates: number;
};

export async function loadLoanApps(
  filters: { q?: string; email?: string; domain?: string } = {},
  signal?: AbortSignal,
): Promise<LoanAppRecord[]> {
  const params = new URLSearchParams();
  if (filters.q?.trim()) params.set("q", filters.q.trim());
  if (filters.email?.trim()) params.set("email", filters.email.trim());
  if (filters.domain?.trim()) params.set("domain", filters.domain.trim());
  const suffix = params.size ? `?${params.toString()}` : "";
  const response = await fetch(`/api/v1/apps${suffix}`, { signal });
  if (!response.ok) throw new Error(`app registry request failed (${response.status})`);
  return response.json() as Promise<LoanAppRecord[]>;
}

export async function loadAppRegistrySummary(signal?: AbortSignal): Promise<AppRegistrySummary> {
  const response = await fetch("/api/v1/apps/summary", { signal });
  if (!response.ok) throw new Error(`app registry summary failed (${response.status})`);
  return response.json() as Promise<AppRegistrySummary>;
}

export async function importPlayApps(records: PlayImportRecord[]): Promise<PlayImportResult> {
  const response = await fetch("/api/v1/apps/import/play", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-KDR-Local-Action": "import_apps",
    },
    body: JSON.stringify({ records }),
  });
  if (!response.ok) throw new Error(`Play app import failed (${response.status})`);
  return response.json() as Promise<PlayImportResult>;
}

export async function reconcileLoanApp(appId: string): Promise<void> {
  const response = await fetch(`/api/v1/apps/${encodeURIComponent(appId)}/ownership/reconcile`, {
    method: "POST",
    headers: { "X-KDR-Local-Action": "reconcile_apps" },
  });
  if (!response.ok) throw new Error(`app ownership reconciliation failed (${response.status})`);
}

export async function reviewAppOwnership(
  linkId: string,
  decision: "confirmed" | "rejected",
): Promise<void> {
  const response = await fetch(`/api/v1/apps/ownership/${encodeURIComponent(linkId)}/review`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-KDR-Local-Action": "review_app_owner",
    },
    body: JSON.stringify({ decision }),
  });
  if (!response.ok) throw new Error(`app ownership review failed (${response.status})`);
}
