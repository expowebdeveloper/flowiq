import { apiClient, runApiCall } from "./apiClient"

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
  /** true = Annual Income document received and matches the declared amount; false = received but didn't match; null/undefined = not received yet. */
  annual_income_verified?: boolean | null
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

export interface LeadDocument {
  id: string
  filename: string
  content_type: string | null
  label: string | null
  content_verified: boolean | null
  uploaded_at: string
}

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

  getDocuments: (id: string) =>
    runApiCall<LeadDocument[]>({
      method: "GET",
      url: `/loan-apply/${encodeURIComponent(id)}/documents`,
    }),

  /**
   * Downloads one document and saves it via the browser, rather than
   * window.open()-ing the raw API URL — that would hit the endpoint with no
   * Authorization header (apiClient's Bearer token is attached by an axios
   * interceptor, not something a plain <a href> or new tab carries), which
   * require_broker would reject with a 401.
   */
  async downloadDocument(submissionId: string, documentId: string, filename: string) {
    const response = await apiClient.get(
      `/loan-apply/${encodeURIComponent(submissionId)}/documents/${encodeURIComponent(documentId)}`,
      { responseType: "blob" },
    )
    const blobUrl = window.URL.createObjectURL(response.data as Blob)
    const link = document.createElement("a")
    link.href = blobUrl
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(blobUrl)
  },

  /**
   * Opens one document in a new tab for previewing (image/PDF) instead of
   * forcing a save-as — same auth problem as downloadDocument (a plain
   * window.open(apiUrl) carries no Authorization header), so this fetches
   * the blob first and opens an object URL instead. Passes
   * disposition=inline so the backend's Content-Disposition header doesn't
   * force a download regardless of how the tab is opened. The object URL is
   * intentionally not revoked here (unlike downloadDocument's) — revoking
   * immediately would blank the tab before it finishes loading the file;
   * it's cleaned up when the browser tab/blob is later garbage collected.
   */
  async viewDocument(submissionId: string, documentId: string) {
    const response = await apiClient.get(
      `/loan-apply/${encodeURIComponent(submissionId)}/documents/${encodeURIComponent(documentId)}`,
      { responseType: "blob", params: { disposition: "inline" } },
    )
    const blobUrl = window.URL.createObjectURL(response.data as Blob)
    window.open(blobUrl, "_blank", "noopener,noreferrer")
  },
}
