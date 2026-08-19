export type BRSEvidenceDocument = {
  id: string;
  sha256: string;
  document_type: "brs_cr12" | "brs_beneficial_ownership_search";
  source_authority: string;
  page_count: number;
  company_name: string | null;
  registration_number: string | null;
  application_number: string | null;
  verification_state: "uploaded_unverified" | "manual_verified" | "rejected";
  verified_by: string | null;
  verified_at: string | null;
  created_at: string;
};

export type BRSVerificationGuidance = {
  automatic_public_api_available: boolean;
  reason: string;
  official_verify_url: string;
  official_search_url: string;
  beneficial_ownership_form_url: string;
  researched_at: string;
};

export async function loadBRSEvidence(signal?: AbortSignal): Promise<BRSEvidenceDocument[]> {
  const response = await fetch("/api/v1/evidence/brs", { signal });
  if (!response.ok) throw new Error(`BRS evidence request failed (${response.status})`);
  return response.json() as Promise<BRSEvidenceDocument[]>;
}

export async function loadBRSVerificationGuidance(signal?: AbortSignal): Promise<BRSVerificationGuidance> {
  const response = await fetch("/api/v1/evidence/brs/verification-guidance", { signal });
  if (!response.ok) throw new Error(`BRS verification guidance failed (${response.status})`);
  return response.json() as Promise<BRSVerificationGuidance>;
}

export async function uploadBRSEvidence(
  file: File,
  documentType: BRSEvidenceDocument["document_type"],
): Promise<BRSEvidenceDocument> {
  const response = await fetch("/api/v1/evidence/brs", {
    method: "POST",
    headers: {
      "Content-Type": "application/pdf",
      "X-KDR-Local-Action": "upload_evidence",
      "X-KDR-Document-Type": documentType,
    },
    body: file,
  });
  if (!response.ok) throw new Error(`BRS evidence upload failed (${response.status})`);
  return response.json() as Promise<BRSEvidenceDocument>;
}

export async function reviewBRSEvidence(
  documentId: string,
  decision: "manual_verified" | "rejected",
): Promise<BRSEvidenceDocument> {
  const response = await fetch(`/api/v1/evidence/brs/${encodeURIComponent(documentId)}/review`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-KDR-Local-Action": "review_evidence",
    },
    body: JSON.stringify({ decision }),
  });
  if (!response.ok) throw new Error(`BRS evidence review failed (${response.status})`);
  return response.json() as Promise<BRSEvidenceDocument>;
}
