import { apiClient, runApiCall } from "./apiClient"
import type { LeadDocument } from "./loanApplyService"

export type BankDecisionStatus = "rejected" | "offer" | "offer_more_documents"

export interface BankDecision {
  id: string
  status: BankDecisionStatus
  remarks: string | null
  decided_at: string
  agent_notified_at: string | null
}

export interface BankNotification {
  id: string
  submission_id: string
  created_at: string
  read_at: string | null
  applicant_name: string | null
  applicant_email: string | null
  loan_type: string | null
  loan_amount: number | null
  fico_score: number | null
  decision: BankDecision | null
}

export interface BankNotificationListResult {
  count: number
  unread_count: number
  notifications: BankNotification[]
}

export const bankNotificationService = {
  list: () =>
    runApiCall<BankNotificationListResult>({
      method: "GET",
      url: "/bank-notifications",
    }),

  markRead: (id: string) =>
    runApiCall<{ id: string; read_at: string }>({
      method: "POST",
      url: `/bank-notifications/${encodeURIComponent(id)}/read`,
    }),

  markAllRead: () =>
    runApiCall<{ updated_count: number }>({
      method: "POST",
      url: "/bank-notifications/read-all",
    }),

  getPdf: (id: string) =>
    runApiCall<Blob>({
      method: "GET",
      url: `/bank-notifications/${encodeURIComponent(id)}/pdf`,
      responseType: "blob",
    }),

  recordDecision: (id: string, status: BankDecisionStatus, remarks: string | null) =>
    runApiCall<BankDecision>({
      method: "POST",
      url: `/bank-notifications/${encodeURIComponent(id)}/decision`,
      data: { status, remarks },
    }),

  getDocuments: (notificationId: string) =>
    runApiCall<LeadDocument[]>({
      method: "GET",
      url: `/bank-notifications/${encodeURIComponent(notificationId)}/documents`,
    }),

  /** Same rationale as loanApplyService.downloadDocument — see its docstring. */
  async downloadDocument(notificationId: string, documentId: string, filename: string) {
    const response = await apiClient.get(
      `/bank-notifications/${encodeURIComponent(notificationId)}/documents/${encodeURIComponent(documentId)}`,
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

  /** Same rationale as loanApplyService.viewDocument — see its docstring. */
  async viewDocument(notificationId: string, documentId: string) {
    const response = await apiClient.get(
      `/bank-notifications/${encodeURIComponent(notificationId)}/documents/${encodeURIComponent(documentId)}`,
      { responseType: "blob", params: { disposition: "inline" } },
    )
    const blobUrl = window.URL.createObjectURL(response.data as Blob)
    window.open(blobUrl, "_blank", "noopener,noreferrer")
  },
}
