export type SourceStatus = {
  snapshot_id: string;
  sha256: string;
  retrieved_at: string;
  record_count: number;
};

export type DashboardSummary = {
  project_status: string;
  regulatory_sources?: string[];
  counts: {
    cbk_dcp_reference_count: number;
    odpc_synced: boolean;
    open_requests: number;
    manual_review: number;
  };
  sources: Record<string, SourceStatus>;
  disclaimer?: string;
};

export type SourceSyncResult = {
  source_id: string;
  snapshot_id: string;
  sha256: string;
  record_count: number;
};

export type ReconciliationRunResult = {
  cbk_snapshot_id: string;
  odpc_snapshot_id: string;
  finding_count: number;
};

const ALPHA_SOURCE_IDS = ["cbk_dcp", "odpc_registered"] as const;

export async function loadDashboardSummary(signal?: AbortSignal): Promise<DashboardSummary> {
  const response = await fetch("/api/v1/dashboard/summary", { signal });
  if (!response.ok) {
    throw new Error(`dashboard summary request failed (${response.status})`);
  }
  return response.json() as Promise<DashboardSummary>;
}

export async function syncSource(sourceId: string): Promise<SourceSyncResult> {
  const response = await fetch(`/api/v1/sources/${encodeURIComponent(sourceId)}/sync`, {
    method: "POST",
    headers: { "X-KDR-Local-Action": "sync" },
  });
  if (!response.ok) {
    throw new Error(`source synchronization failed (${response.status})`);
  }
  return response.json() as Promise<SourceSyncResult>;
}

export async function runReconciliation(): Promise<ReconciliationRunResult> {
  const response = await fetch("/api/v1/reconciliation/cbk-odpc/run", {
    method: "POST",
    headers: { "X-KDR-Local-Action": "reconcile" },
  });
  if (!response.ok) {
    throw new Error(`reconciliation failed (${response.status})`);
  }
  return response.json() as Promise<ReconciliationRunResult>;
}

export async function syncAlphaSources(): Promise<string[]> {
  const failures: string[] = [];
  for (const sourceId of ALPHA_SOURCE_IDS) {
    try {
      await syncSource(sourceId);
    } catch {
      failures.push(sourceId);
    }
  }
  if (failures.length === 0) {
    try {
      await runReconciliation();
    } catch {
      failures.push("reconciliation");
    }
  }
  return failures;
}
