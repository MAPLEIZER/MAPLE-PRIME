export type LoanPricingRecord = {
  id: string;
  app_id: string;
  institution_id: string | null;
  source_type: string;
  source_provider: string;
  source_url: string | null;
  observed_at: string;
  currency: string;
  amount_received: string;
  total_repayment: string;
  term_days: number;
  advertised_interest_rate_percent: string | null;
  advertised_rate_basis: string;
  interest_amount: string;
  processing_fee: string;
  service_fee: string;
  insurance_fee: string;
  disbursement_fee: string;
  other_mandatory_fees: string;
  disclosed_late_fee: string;
  disclosed_rollover_fee: string;
  effective_cost_amount: string;
  effective_cost_percent: string;
  known_cost_amount: string;
  unexplained_cost_amount: string;
};

export type LoanPricingInput = {
  app_id: string;
  institution_id?: string | null;
  source_type: "public_disclosure" | "marketplace_listing" | "borrower_report" | "manual_test" | "regulator_publication";
  source_provider: string;
  source_url?: string | null;
  observed_at: string;
  currency: string;
  amount_received: string;
  total_repayment: string;
  term_days: number;
  advertised_interest_rate_percent?: string | null;
  advertised_rate_basis: "daily" | "weekly" | "monthly" | "term" | "annual" | "unspecified";
  interest_amount: string;
  processing_fee: string;
  service_fee: string;
  insurance_fee: string;
  disbursement_fee: string;
  other_mandatory_fees: string;
  disclosed_late_fee: string;
  disclosed_rollover_fee: string;
};

export async function loadPricing(appId?: string, signal?: AbortSignal): Promise<LoanPricingRecord[]> {
  const params = new URLSearchParams();
  if (appId?.trim()) params.set("app_id", appId.trim());
  const suffix = params.size ? `?${params.toString()}` : "";
  const response = await fetch(`/api/v1/pricing${suffix}`, { signal });
  if (!response.ok) throw new Error(`pricing history request failed (${response.status})`);
  return response.json() as Promise<LoanPricingRecord[]>;
}

export async function recordPricing(payload: LoanPricingInput): Promise<LoanPricingRecord> {
  const response = await fetch("/api/v1/pricing", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-KDR-Local-Action": "record_pricing",
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(`pricing observation save failed (${response.status})`);
  return response.json() as Promise<LoanPricingRecord>;
}
