import { runApiCall } from "./apiClient"

export type AiActivitySource = "mailbox_poll" | "document_processing" | "email_agent" | "bank_notify" | "bank_decision"
export type AiActivityStatus = "started" | "info" | "success" | "error"

export interface AiActivityEvent {
  id: string
  created_at: string
  source: AiActivitySource
  status: AiActivityStatus
  message: string
  submission_id: string | null
  detail: Record<string, unknown> | null
}

export interface AiActivityListResult {
  events: AiActivityEvent[]
}

export const aiActivityService = {
  list: (limit?: number) =>
    runApiCall<AiActivityListResult>({
      method: "GET",
      url: "/agent-activity",
      params: limit ? { limit } : undefined,
    }),

  listForSubmission: (submissionId: string, limit?: number) =>
    runApiCall<AiActivityListResult>({
      method: "GET",
      url: "/agent-activity",
      params: { submission_id: submissionId, ...(limit ? { limit } : {}) },
    }),
}
