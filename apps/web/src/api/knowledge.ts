export interface LegalEntry {
  id: string;
  title: string;
  citation: string;
  summary: string;
  topics: string[];
  provisions: string[];
  sourceUrl: string;
  sourceDate: string;
  caution: string;
}

export interface CivicChannel {
  kind: "email" | "form";
  label: string;
  url?: string | null;
  recipients?: string[];
}

export interface Consultation {
  id: string;
  title: string;
  agency: string;
  status: "open" | "closed" | "upcoming";
  deadline: string;
  topics: string[];
  sourceUrl: string;
  channels: CivicChannel[];
}

export interface CivicDraftResult {
  subject: string;
  body: string;
  sent: false;
  requiresUserReview: true;
  submissionAllowed: boolean;
  mailtoLinks: Array<{ label: string; url: string }>;
  formLinks: Array<{ label: string; url: string }>;
}

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json() as Promise<T>;
}

export async function loadLegalLibrary(signal?: AbortSignal): Promise<LegalEntry[]> {
  const rows = await json<Array<Record<string, unknown>>>("/api/v1/legal/library", { signal });
  return rows.map((row) => ({
    id: String(row.id),
    title: String(row.title),
    citation: String(row.citation),
    summary: String(row.summary),
    topics: row.topics as string[],
    provisions: row.provisions as string[],
    sourceUrl: String(row.source_url),
    sourceDate: String(row.source_date),
    caution: String(row.caution),
  }));
}

export async function loadConsultations(signal?: AbortSignal): Promise<Consultation[]> {
  const rows = await json<Array<Record<string, unknown>>>("/api/v1/civic/consultations", { signal });
  return rows.map((row) => ({
    id: String(row.id),
    title: String(row.title),
    agency: String(row.agency),
    status: row.status as Consultation["status"],
    deadline: String(row.deadline),
    topics: row.topics as string[],
    sourceUrl: String(row.source_url),
    channels: row.channels as CivicChannel[],
  }));
}

export async function draftConsultation(
  consultationId: string,
  input: { submitterName: string; position: string; points: string[] },
): Promise<CivicDraftResult> {
  const row = await json<Record<string, unknown>>(`/api/v1/civic/consultations/${encodeURIComponent(consultationId)}/draft`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      consultation_id: consultationId,
      submitter_name: input.submitterName,
      position: input.position,
      points: input.points,
    }),
  });
  return {
    subject: String(row.subject),
    body: String(row.body),
    sent: false,
    requiresUserReview: true,
    submissionAllowed: Boolean(row.submission_allowed),
    mailtoLinks: row.mailto_links as CivicDraftResult["mailtoLinks"],
    formLinks: row.form_links as CivicDraftResult["formLinks"],
  };
}
