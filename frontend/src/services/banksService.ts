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
} from "@/types/api"

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
    runApiCall<BankListResponse>({ method: "GET", url: "/banks" }),

  createBank: (payload: { name: string; website?: string; logo?: string; status?: string }) =>
    runApiCall({ method: "POST", url: "/banks/add", data: payload }),

  updateBank: (bankId: number, payload: { name: string; website?: string; logo?: string; status?: string }) =>
    runApiCall({ method: "POST", url: `/banks/${bankId}/edit`, data: payload }),

  deleteBank: (bankId: number) =>
    runApiCall({ method: "POST", url: `/banks/${bankId}/delete` }),

  // Bank Policies (CRUD)
  listBankPolicies: (bankId: number) =>
    runApiCall<LoanPolicyListResponse>({ method: "GET", url: `/banks/${bankId}/policies` }),

  createBankPolicy: (bankId: number, payload: Omit<LoanPolicy, "id" | "bank_id">) =>
    runApiCall({ method: "POST", url: `/banks/${bankId}/policies/add`, data: payload }),

  updateBankPolicy: (policyId: number, payload: Omit<LoanPolicy, "id" | "bank_id">) =>
    runApiCall({ method: "POST", url: `/banks/policies/${policyId}/edit`, data: payload }),

  deleteBankPolicy: (policyId: number) =>
    runApiCall({ method: "POST", url: `/banks/policies/${policyId}/delete` }),
}
