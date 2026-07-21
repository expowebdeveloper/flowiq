// ─── Auth ──────────────────────────────────────────────────────────────────

export type UserRole = "broker" | "user" | "bank"

export interface CurrentUser {
  id: string
  email: string
  role: UserRole
  bank_name?: string | null
}

export interface AuthStatusResponse {
  email: string
  linked: boolean
}

export interface LoginResponse {
  token: string
  email: string
  role: UserRole
  bank_name?: string | null
}

// ─── Inbox / Inbound ───────────────────────────────────────────────────────

export interface EmailAttachment {
  filename: string
  mime_type: string
  size_bytes: number
  download_url: string
  saved_path?: string
}

export interface InboxMessageSummary {
  id: string
  thread_id: string
  subject: string
  from: string
  to: string
  date: string
  snippet: string
  has_attachment: boolean
  labels: string[]
}

export interface InboxListResponse {
  email: string
  total_fetched: number
  next_page_token: string | null
  messages: InboxMessageSummary[]
}

export interface InboxFullMessage {
  id: string
  thread_id: string
  subject: string
  from: string
  to: string
  cc?: string
  date: string
  snippet: string
  body_text: string
  body_html: string
  labels: string[]
  attachments: EmailAttachment[]
}

export interface InboxFullResponse {
  email: string
  total_fetched: number
  emails: InboxFullMessage[]
}

export interface InboxThreadResponse {
  email: string
  thread_id: string
  total_messages: number
  messages: InboxFullMessage[]
}

// ─── Outbound ──────────────────────────────────────────────────────────────

export interface SendEmailRequest {
  email: string
  to: string
  subject: string
  body: string
  reply_to_message_id?: string
  thread_id?: string
  cc?: string
}

export interface SendEmailResponse {
  message_id: string
  thread_id: string
  status: string
}

// ─── Agents ────────────────────────────────────────────────────────────────

export interface AgentRunRequest {
  email: string
  task?: string
}

export interface AgentRunResponse {
  task_id: string
  status: string
  message: string
}

export interface AgentStatusResponse {
  task_id: string
  status: string
  result: unknown
}

// ─── Banks — Loan Categories ────────────────────────────────────────────────

export const LOAN_TYPES = [
  "home_loan",
  "education_loan",
  "personal_loan",
  "car_loan",
  "gold_loan",
] as const

export type LoanType = (typeof LOAN_TYPES)[number]

export interface LoanCategory {
  id: string
  type: string
}

export interface LoanCategoriesResponse {
  available_types: string[]
  categories: LoanCategory[]
}

export interface LoanCategoryRequest {
  type: string
}

// ─── Banks — Loan Rates ──────────────────────────────────────────────────────

export interface BankLoanRateEntry {
  bank_name: string
  loan_type: string
  interest_rate: string
  details?: string
  required_documents?: string
  source_url?: string
}

export interface BankLoanRate extends BankLoanRateEntry {
  id: string
  required_documents_list: string[]
  updated_at: string
}

export interface BankLoanRatesBulkRequest {
  rates: BankLoanRateEntry[]
}

export interface BankLoanRatesBulkResponse {
  status: string
  count: number
  rates: BankLoanRate[]
}

export interface BankLoanRatesListResponse {
  count: number
  rates: BankLoanRate[]
}

// ─── Banks — Loan Applications ───────────────────────────────────────────────

export interface LoanApplicationDocument {
  id: string
  filename: string
  content_type: string
  label: string | null
  download_url: string
}

export interface LoanApplication {
  id: string
  broker_id: string
  bank_loan_rate_id: string
  bank_name: string
  loan_type: string
  applicant_name: string
  applicant_phone: string
  applicant_email: string | null
  notes: string | null
  status: string
  created_at: string
  documents: LoanApplicationDocument[]
}

export interface LoanApplicationsListResponse {
  count: number
  applications: LoanApplication[]
}

// ─── KYC ───────────────────────────────────────────────────────────────────

export interface KycApplicationDetail {
  bank_name: string
  loan_type: string
  loan_types: string[]
  applicant_name: string
  applicant_phone: string
  applicant_email: string | null
  date_of_birth: string | null
  gender: string | null
  address: string | null
  required_documents: string | null
}

export interface KycSubmitResponse {
  status: string
  message: string
  bank_notified: boolean
  banks_notified_count: number
  bank_notification_warning: string | null
}

// ─── Bank Management ─────────────────────────────────────────────────────────

export interface Bank {
  id: number
  name: string
  website: string | null
  logo: string | null
  status: string
  contact_email: string | null
  // Portal login for a future agent-automation pass — not wired up to
  // anything yet, storage only.
  portal_url: string | null
  portal_username: string | null
  portal_password: string | null
  updated_at?: string
}

export interface BankListResponse {
  success: boolean
  banks: Bank[]
}

export interface LoanPolicy {
  id: number
  bank_id: number
  loan_type: string
  // Every field below is null until an admin fills in the full policy
  // details — toggling a loan type "on" for a bank creates a bare row with
  // just loan_type set.
  min_cibil: number | null
  max_cibil: number | null
  min_income: number | null
  max_loan_amount: number | null
  interest_rate: number | null
  processing_fee: number | null
  max_ltv: number | null
  min_age: number | null
  max_age: number | null
  minimum_work_experience_years: number | null
  maximum_foir: number | null
  employment_types: string | null
  property_types: string | null
  required_documents: string | null
  special_features: string | null
  prepayment_charges: string | null
  foreclosure_charges: string | null
  min_tenure: number | null
  max_tenure: number | null
  last_updated?: string
}

export interface LoanPolicyListResponse {
  success: boolean
  bank_id: number
  policies: LoanPolicy[]
}

// ─── Loan Requirements (agent instruction library) ──────────────────────────
// Backend model/table is named AgentCommand/agent_commands — an internal
// implementation detail; the frontend-facing name matches the "Loan
// Requirements" page and domain language.

export interface LoanRequirement {
  id: number
  scenario: string
  instruction: string
  loan_types: string[] // empty = applies to every loan type; otherwise one or more specific types
  bank_id: number | null // null = global requirement, not bank-specific
  attachment_filename: string | null // original filename, for display
  attachment_url: string | null // download URL, present only if an attachment exists
  created_at?: string
  updated_at?: string
}

export interface LoanRequirementListResponse {
  success: boolean
  bank_id?: number
  commands: LoanRequirement[]
}

// ─── Chat ────────────────────────────────────────────────────────────────────

export interface ChatUser {
  id: string
  email: string
  role: UserRole
}

export interface ChatMessage {
  id: string
  sender_id: string
  recipient_id: string
  body: string
  created_at: string
}

// ─── Errors ──────────────────────────────────────────────────────────────────

export interface ValidationError {
  loc: (string | number)[]
  msg: string
  type: string
}

export interface HTTPValidationError {
  detail: ValidationError[] | string
}
