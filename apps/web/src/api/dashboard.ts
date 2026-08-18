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

export type ReconciliationFinding = {
  id: string;
  finding_type: string;
  confidence: number;
  summary: string;
  review_state: string;
  left_source_key: string;
  right_source_key: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
};

export type ReconciliationReviewResult = {
  id: string;
  review_state: "confirmed" | "rejected";
  reviewed_by: string;
  reviewed_at?: string | null;
  resolved_institution_id?: string | null;
};

export type SyncStageId = "cbk_dcp" | "odpc_registered" | "reconciliation";
export type SyncStageState = "running" | "success" | "failed" | "skipped";

export type SyncStageEvent = {
  stage: SyncStageId;
  state: SyncStageState;
  label: string;
  detail?: string;
};

export type SyncFailure = {
  stage: SyncStageId;
  code: string;
  message: string;
};

export type SyncRunReport = {
  failures: SyncFailure[];
  succeeded: SyncStageId[];
};

const ALPHA_SOURCE_IDS = ["cbk_dcp", "odpc_registered"] as const;

const STAGE_LABELS: Record<SyncStageId, string> = {
  cbk_dcp: "CBK digital credit providers",
  odpc_registered: "ODPC registered data handlers",
  reconciliation: "CBK ↔ ODPC reconciliation",
};

export class SourceSyncError extends Error {
  readonly sourceId: string;
  readonly code: string;

  constructor(sourceId: string, code: string, message: string) {
    super(message);
    this.name = "SourceSyncError";
    this.sourceId = sourceId;
    this.code = code;
  }
}

export async function loadDashboardSummary(signal?: AbortSignal): Promise<DashboardSummary> {
  const response = await fetch("/api/v1/dashboard/summary", { signal });
  if (!response.ok) {
    throw new Error(`dashboard summary request failed (${response.status})`);
  }
  return response.json() as Promise<DashboardSummary>;
}

export async function loadReconciliationFindings(
  signal?: AbortSignal,
  limit = 500,
): Promise<ReconciliationFinding[]> {
  const safeLimit = Math.max(1, Math.min(limit, 1000));
  const response = await fetch(`/api/v1/reconciliation/findings?limit=${safeLimit}`, { signal });
  if (!response.ok) {
    throw new Error(`reconciliation findings request failed (${response.status})`);
  }
  return response.json() as Promise<ReconciliationFinding[]>;
}

async function sourceSyncFailure(response: Response, sourceId: string): Promise<SourceSyncError> {
  try {
    const payload = await response.json() as { detail?: unknown };
    if (payload.detail && typeof payload.detail === "object") {
      const detail = payload.detail as Record<string, unknown>;
      const code = typeof detail.code === "string" ? detail.code : "source_sync_failed";
      const message = typeof detail.message === "string"
        ? detail.message
        : `Source synchronization failed (${response.status}).`;
      return new SourceSyncError(sourceId, code, message);
    }
  } catch {
    // Fall back to a bounded generic message; never surface raw response bodies.
  }
  return new SourceSyncError(sourceId, "source_sync_failed", `Source synchronization failed (${response.status}).`);
}

export async function syncSource(sourceId: string): Promise<SourceSyncResult> {
  const response = await fetch(`/api/v1/sources/${encodeURIComponent(sourceId)}/sync`, {
    method: "POST",
    headers: { "X-KDR-Local-Action": "sync" },
  });
  if (!response.ok) {
    throw await sourceSyncFailure(response, sourceId);
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

export async function reviewFinding(
  findingId: string,
  decision: "confirmed" | "rejected",
): Promise<ReconciliationReviewResult> {
  const response = await fetch(
    `/api/v1/reconciliation/findings/${encodeURIComponent(findingId)}/review`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-KDR-Local-Action": "review",
      },
      body: JSON.stringify({ decision }),
    },
  );
  if (!response.ok) {
    throw new Error(`reconciliation review failed (${response.status})`);
  }
  return response.json() as Promise<ReconciliationReviewResult>;
}

export async function syncAlphaSources(
  onStage?: (event: SyncStageEvent) => void,
): Promise<SyncRunReport> {
  const failures: SyncFailure[] = [];
  const succeeded: SyncStageId[] = [];

  for (const sourceId of ALPHA_SOURCE_IDS) {
    onStage?.({ stage: sourceId, state: "running", label: STAGE_LABELS[sourceId] });
    try {
      const result = await syncSource(sourceId);
      succeeded.push(sourceId);
      onStage?.({
        stage: sourceId,
        state: "success",
        label: STAGE_LABELS[sourceId],
        detail: `${result.record_count} records imported`,
      });
    } catch (error) {
      const failure = error instanceof SourceSyncError
        ? { stage: sourceId, code: error.code, message: error.message }
        : { stage: sourceId, code: "source_sync_failed", message: "Source synchronization failed." };
      failures.push(failure);
      onStage?.({ stage: sourceId, state: "failed", label: STAGE_LABELS[sourceId], detail: failure.message });
    }
  }

  if (failures.length === 0) {
    onStage?.({ stage: "reconciliation", state: "running", label: STAGE_LABELS.reconciliation });
    try {
      const result = await runReconciliation();
      succeeded.push("reconciliation");
      onStage?.({
        stage: "reconciliation",
        state: "success",
        label: STAGE_LABELS.reconciliation,
        detail: `${result.finding_count} findings prepared for review`,
      });
    } catch {
      const failure = {
        stage: "reconciliation" as const,
        code: "reconciliation_failed",
        message: "Both source snapshots were saved, but reconciliation could not complete.",
      };
      failures.push(failure);
      onStage?.({ stage: "reconciliation", state: "failed", label: STAGE_LABELS.reconciliation, detail: failure.message });
    }
  } else {
    onStage?.({
      stage: "reconciliation",
      state: "skipped",
      label: STAGE_LABELS.reconciliation,
      detail: "Skipped until both regulator sources have current snapshots.",
    });
  }

  return { failures, succeeded };
}
