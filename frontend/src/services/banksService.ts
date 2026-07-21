import { runApiCall } from "./apiClient"
import type {
  BankLoanRateEntry,
  BankLoanRatesBulkRequest,
  BankLoanRatesBulkResponse,
  BankLoanRatesListResponse,
  LoanApplication,
  LoanApplicationsListResponse,
  LoanCategoriesResponse,
  LoanCategoryRequest,
  BankListResponse,
  LoanPolicy,
  LoanPolicyListResponse,
  LoanRequirementListResponse,
} from "@/types/api"

export interface BankPayload {
  name: string
  website?: string
  logo?: string
  status?: string
  contact_email?: string
  portal_url?: string
  portal_username?: string
  portal_password?: string
}

// Only loan_type is required — toggling a loan type "on" from the Bank
// Detail page creates a bare policy with everything else left null, to be
// filled in later via the full Add/Edit Loan Policy modal.
export type LoanPolicyPayload = Partial<Omit<LoanPolicy, "id" | "bank_id">> & {
  loan_type: string
}

export interface LoanRequirementPayload {
  scenario: string
  instruction: string
  loan_types: string[] // empty = applies to every loan type
  attachmentFile?: File | null // a newly-chosen file to upload
  removeAttachment?: boolean // when editing, clear an existing attachment without replacing it
}

function buildRequirementFormData(payload: LoanRequirementPayload): FormData {
  const formData = new FormData()
  formData.append("scenario", payload.scenario)
  formData.append("instruction", payload.instruction)
  formData.append("loan_types", payload.loan_types.join(","))
  if (payload.attachmentFile) formData.append("attachment", payload.attachmentFile)
  if (payload.removeAttachment) formData.append("remove_attachment", "true")
  return formData
}

export interface BankCreateResponse {
  success: boolean
  message: string
  bank_id: number | null
}

export const banksService = {
  // Loan categories (broker only)
  listCategories: () =>
    runApiCall<LoanCategoriesResponse>({ method: "GET", url: "/broker/loan-categories" }),

  createCategory: (payload: LoanCategoryRequest) =>
    runApiCall({ method: "POST", url: "/broker/loan-categories", data: payload }),

  deleteCategory: (categoryId: string) =>
    runApiCall({
      method: "DELETE",
      url: `/broker/loan-categories/${encodeURIComponent(categoryId)}`,
    }),

  // Loan rates
  createRate: (payload: BankLoanRateEntry) =>
    runApiCall({ method: "POST", url: "/bank-loan-rates/bank", data: payload }),

  bulkUpsertRates: (payload: BankLoanRatesBulkRequest) =>
    runApiCall<BankLoanRatesBulkResponse>({
      method: "POST",
      url: "/bank-loan-rates",
      data: payload,
    }),

  listRates: (params?: { bank_name?: string; loan_type?: string }) =>
    runApiCall<BankLoanRatesListResponse>({
      method: "GET",
      url: "/bank-loan-rates",
      params,
    }),

  // Loan applications (broker only, multipart)
  submitApplication: (formData: FormData) =>
    runApiCall<LoanApplication>({
      method: "POST",
      url: "/loan-applications",
      data: formData,
      headers: { "Content-Type": "multipart/form-data" },
    }),

  listApplications: () =>
    runApiCall<LoanApplicationsListResponse>({ method: "GET", url: "/loan-applications" }),

  // Loan applications (bank login only) — applications submitted for the logged-in bank
  listApplicationsForBank: () =>
    runApiCall<LoanApplicationsListResponse>({ method: "GET", url: "/loan-applications/bank" }),

  documentDownloadPath: (applicationId: string, documentId: string) =>
    `/loan-applications/${encodeURIComponent(applicationId)}/documents/${encodeURIComponent(documentId)}`,

  // Bank Management (CRUD)
  listBanks: () =>
    runApiCall<BankListResponse>({ method: "GET", url: "/banks/" }),

  createBank: (payload: BankPayload) =>
    runApiCall<BankCreateResponse>({ method: "POST", url: "/banks/add", data: payload }),

  updateBank: (bankId: number, payload: BankPayload) =>
    runApiCall({ method: "POST", url: `/banks/${bankId}/edit`, data: payload }),

  deleteBank: (bankId: number) =>
    runApiCall({ method: "POST", url: `/banks/${bankId}/delete` }),

  // Bank Policies (CRUD)
  listBankPolicies: (bankId: number) =>
    runApiCall<LoanPolicyListResponse>({ method: "GET", url: `/banks/${bankId}/policies` }),

  createBankPolicy: (bankId: number, payload: LoanPolicyPayload) =>
    runApiCall({ method: "POST", url: `/banks/${bankId}/policies/add`, data: payload }),

  updateBankPolicy: (policyId: number, payload: LoanPolicyPayload) =>
    runApiCall({ method: "POST", url: `/banks/policies/${policyId}/edit`, data: payload }),

  deleteBankPolicy: (policyId: number) =>
    runApiCall({ method: "POST", url: `/banks/policies/${policyId}/delete` }),

  // Loan Requirements — global (bank_id is always null server-side)
  listGlobalRequirements: () =>
    runApiCall<LoanRequirementListResponse>({ method: "GET", url: "/agent-commands" }),

  createGlobalRequirement: (payload: LoanRequirementPayload) =>
    runApiCall({
      method: "POST",
      url: "/agent-commands/add",
      data: buildRequirementFormData(payload),
      headers: { "Content-Type": "multipart/form-data" },
    }),

  // Loan Requirements — scoped to one bank
  listBankRequirements: (bankId: number) =>
    runApiCall<LoanRequirementListResponse>({ method: "GET", url: `/banks/${bankId}/commands` }),

  createBankRequirement: (bankId: number, payload: LoanRequirementPayload) =>
    runApiCall({
      method: "POST",
      url: `/banks/${bankId}/commands/add`,
      data: buildRequirementFormData(payload),
      headers: { "Content-Type": "multipart/form-data" },
    }),

  // Shared edit/delete — a requirement's id is enough regardless of scope
  updateRequirement: (requirementId: number, payload: LoanRequirementPayload) =>
    runApiCall({
      method: "POST",
      url: `/agent-commands/${requirementId}/edit`,
      data: buildRequirementFormData(payload),
      headers: { "Content-Type": "multipart/form-data" },
    }),

  deleteRequirement: (requirementId: number) =>
    runApiCall({ method: "POST", url: `/agent-commands/${requirementId}/delete` }),
}
