export type ContributionKind = "sms_sender" | "call_number" | "app_package";

export interface LocalObservation {
  kind: ContributionKind;
  institutionHint?: string;
  senderIdentifier?: string;
  appPackage?: string;
  observedAt?: string;
  rawMessageBody?: string;
  callDurationSeconds?: number;
  shareConsent: boolean;
}

export interface SharedContribution {
  kind: ContributionKind;
  institutionHint?: string;
  senderIdentifier?: string;
  appPackage?: string;
  observedAt?: string;
}

export function prepareContribution(input: LocalObservation): SharedContribution {
  if (!input.shareConsent) {
    throw new Error("Explicit contribution consent is required");
  }
  const output: SharedContribution = { kind: input.kind };
  if (input.institutionHint) output.institutionHint = input.institutionHint;
  if (input.senderIdentifier) output.senderIdentifier = input.senderIdentifier;
  if (input.appPackage) output.appPackage = input.appPackage;
  if (input.observedAt) output.observedAt = input.observedAt;
  return output;
}
