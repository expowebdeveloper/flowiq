import type { LoanApplyResult } from "@/services/loanApplyService"

export type LeadStageKey =
  | "captured"
  | "assessment"
  | "with_banks"
  | "offer_with_docs"
  | "offers"
  | "reject"

export interface LeadStageDef {
  key: LeadStageKey
  label: string
  description: string
}

export const LEAD_STAGE_DEFS: LeadStageDef[] = [
  { key: "captured", label: "Captured", description: "Submitted, awaiting documents" },
  { key: "assessment", label: "Assessment", description: "Documents received, verification incomplete" },
  { key: "with_banks", label: "With banks", description: "Documents verified, synced to banks" },
  { key: "offer_with_docs", label: "Offer with docs", description: "A bank wants to offer but needs more documents to verify" },
  { key: "offers", label: "Offers", description: "A bank has made an offer on the loan application" },
  { key: "reject", label: "Reject", description: "Every responding bank rejected the application" },
]

/**
 * Buckets a lead into exactly one stage — its furthest progress so far.
 * Checked most-advanced-first so a lead with e.g. both an "offer" and a
 * "rejected" decision from different banks lands in Offers, not Reject.
 * Mirrors the actual pipeline: banks are only notified once documents_status
 * becomes "documents_complete" (see backend/loan_apply/document_processing.py),
 * and BankDecision.status is only ever "offer" | "offer_more_documents" |
 * "rejected".
 *
 * Shared by the dashboard's Pipeline by stage widget and the Leads page's
 * stage filter so the two never disagree about which bucket a lead is in.
 */
export function stageOf(lead: LoanApplyResult): LeadStageKey {
  const decisions = lead.bank_decisions
  if (decisions.length > 0 && decisions.every((d) => d.status === "rejected")) return "reject"
  if (decisions.some((d) => d.status === "offer")) return "offers"
  if (decisions.some((d) => d.status === "offer_more_documents")) return "offer_with_docs"
  if (lead.documents_status === "documents_complete") return "with_banks"
  if (lead.documents_status === "documents_incomplete") return "assessment"
  return "captured"
}
