import { runApiCall } from "./apiClient"

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
}
