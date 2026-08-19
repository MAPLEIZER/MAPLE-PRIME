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

export type PlayDiscoveryResult = {
  provider: string;
  providers_considered: number;
  search_requests: number;
  detail_requests: number;
  apps_ingested: number;
  ownership_candidates: number;
  relationship_edges: number;
  failures: string[];
};

export type PlayResearchRequest = {
  provider: "auto" | "serpapi" | "talordata";
  mode: "category" | "query" | "hybrid";
  queries: string[];
  max_pages: number;
  max_apps: number;
  enrich_limit: number;
  skip_existing: boolean;
  match_ownership: boolean;
};

export type PlayResearchRow = {
  package_name: string;
  app_name: string;
  developer_name: string;
  support_email: string | null;
  developer_website: string | null;
  privacy_policy_url: string | null;
  store_url: string;
  category: string | null;
  installs: string | null;
  database_status: "new" | "existing" | "refreshed";
  email_status: "new" | "existing" | "duplicate_in_run" | "none";
  matched_by: string[];
  source_provider: string;
};

export type PlayResearchResult = {
  provider: string;
  mode: string;
  queries: string[];
  search_requests: number;
  pages_fetched: number;
  detail_requests: number;
  unique_apps_discovered: number;
  duplicate_packages_skipped: number;
  new_apps: number;
  existing_apps: number;
  skipped_existing_apps: number;
  apps_ingested: number;
  emails_found: number;
  new_unique_emails: number;
  existing_email_hits: number;
  duplicate_emails_in_run: number;
  ownership_candidates: number;
  relationship_edges: number;
  failures: string[];
  results: PlayResearchRow[];
};

export type PlayDiscoveryStatus = {
  requested_provider: string;
  active_provider: string;
  configured: boolean;
  serpapi_key_configured: boolean;
  talordata_key_configured: boolean;
  public_html_fallback_available: boolean;
  manual_batch: { max_providers: number; max_apps: number };
  research_limits: { max_pages: number; max_apps: number; max_enrichments: number };
  suggested_queries: string[];
  configuration_error: string | null;
  configuration_note: string | null;
  available_providers: string[];
};

export type SerpApiAccountHealth = {
  checked: boolean;
  key_valid: boolean | null;
  account_status: string | null;
  plan_name: string | null;
  searches_left: number | null;
  this_month_usage: number | null;
  this_hour_searches: number | null;
  hourly_limit: number | null;
  plan_renewal_date: string | null;
  error: string | null;
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

export async function loadPlayDiscoveryStatus(signal?: AbortSignal): Promise<PlayDiscoveryStatus> {
  const response = await fetch("/api/v1/apps/discovery/status", { signal });
  if (!response.ok) throw new Error(`Play discovery status failed (${response.status})`);
  return response.json() as Promise<PlayDiscoveryStatus>;
}

export async function loadSerpApiAccountHealth(signal?: AbortSignal): Promise<SerpApiAccountHealth> {
  const response = await fetch("/api/v1/apps/discovery/account", { signal });
  if (!response.ok) throw new Error(`SerpApi account health failed (${response.status})`);
  return response.json() as Promise<SerpApiAccountHealth>;
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

async function discoveryError(response: Response, fallback: string): Promise<Error> {
  let detail = "";
  try {
    const payload = await response.json() as { detail?: { message?: string } | string };
    detail = typeof payload.detail === "string" ? payload.detail : payload.detail?.message ?? "";
  } catch {
    detail = "";
  }
  return new Error(detail || fallback);
}

export async function runPlayResearch(request: PlayResearchRequest): Promise<PlayResearchResult> {
  const response = await fetch("/api/v1/apps/discovery/research", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-KDR-Local-Action": "discover_apps",
    },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw await discoveryError(response, `Play research failed (${response.status})`);
  return response.json() as Promise<PlayResearchResult>;
}

export async function runPlayDiscovery(maxProviders = 5, maxApps = 15): Promise<PlayDiscoveryResult> {
  const params = new URLSearchParams({
    max_providers: String(maxProviders),
    max_apps: String(maxApps),
  });
  const response = await fetch(`/api/v1/apps/discovery/run?${params.toString()}`, {
    method: "POST",
    headers: { "X-KDR-Local-Action": "discover_apps" },
  });
  if (!response.ok) throw await discoveryError(response, `Play discovery failed (${response.status})`);
  return response.json() as Promise<PlayDiscoveryResult>;
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
