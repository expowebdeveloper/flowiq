import { runApiCall } from "./apiClient"

export interface LoanApplyPayload {
  first_name: string
  last_name: string
  email: string
  phone_number: string
  date_of_birth: string
  ssn: string
  gender: string
  citizenship_status: string
  current_address: string
  marital_status: string
  loan_type: string
  fico_score: number
  zip_code: string
  loan_amount: number
  extra_loan_details?: Record<string, string> | null
}

export interface BankDecisionSummary {
  bank_name: string
  status: "rejected" | "offer" | "offer_more_documents"
  remarks: string | null
  decided_at: string
}

export interface LoanApplyResult extends LoanApplyPayload {
  id: string
  created_at: string
  documents_status: string
  extracted_data?: Record<string, string> | null
  documents_processed_at?: string | null
  bank_decisions: BankDecisionSummary[]
}

export interface RequirementField {
  field: string
  label: string
  description: string
}

export interface LoanRequirement {
  mandatory_fields: RequirementField[]
}

export interface LeadCreatedEvent {
  type: "lead_created"
  at_ms: number
  loan_type: string
}

export interface DocumentsProcessedEvent {
  type: "documents_processed"
  at_ms: number
  documents_status: string
}

export interface EmailEvent {
  type: "email"
  direction: "inbound" | "outbound"
  gmail_message_id: string
  from: string
  to: string
  subject: string
  snippet: string
  body: string
  attachments: string[]
  date: string | null
  internal_date_ms: number | null
}

export interface BankDecisionEvent {
  type: "bank_decision"
  at_ms: number
  bank_name: string
  status: "rejected" | "offer" | "offer_more_documents"
  remarks: string | null
}

export type LeadActivityEvent = LeadCreatedEvent | DocumentsProcessedEvent | EmailEvent | BankDecisionEvent

export const loanApplyService = {
  submit: (payload: LoanApplyPayload) =>
    runApiCall<LoanApplyResult>({
      method: "POST",
      url: "/loan-apply",
      data: payload,
    }),

  getRequirements: () =>
    runApiCall<Record<string, LoanRequirement>>({
      method: "GET",
      url: "/loan-apply/requirements",
    }),

  getApplicantEmails: () =>
    runApiCall<string[]>({
      method: "GET",
      url: "/loan-apply/applicant-emails",
    }),

  list: () =>
    runApiCall<LoanApplyResult[]>({
      method: "GET",
      url: "/loan-apply",
    }),

  getById: (id: string) =>
    runApiCall<LoanApplyResult>({
      method: "GET",
      url: `/loan-apply/${encodeURIComponent(id)}`,
    }),

  getActivity: (id: string) =>
    runApiCall<{ events: LeadActivityEvent[] }>({
      method: "GET",
      url: `/loan-apply/${encodeURIComponent(id)}/activity`,
    }),
}
