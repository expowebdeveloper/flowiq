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
  min_cibil: number
  max_cibil: number
  min_income: number
  max_loan_amount: number
  interest_rate: number
  processing_fee: number
  max_ltv: number
  min_age: number
  max_age: number
  minimum_work_experience_years: number
  maximum_foir: number
  employment_types: string
  property_types: string
  required_documents: string
  special_features: string
  prepayment_charges: string
  foreclosure_charges: string
  min_tenure: number
  max_tenure: number
  last_updated?: string
}

export interface LoanPolicyListResponse {
  success: boolean
  bank_id: number
  policies: LoanPolicy[]
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
