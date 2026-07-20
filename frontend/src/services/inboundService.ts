import { runApiCall } from "./apiClient"
import type { InboxFullResponse, InboxListResponse, InboxThreadResponse } from "@/types/api"

export interface GetInboxParams {
  email: string
  max_results?: number
  page_token?: string
  query?: string
}

export interface GetMessageParams {
  message_id: string
  email: string
  download_attachments?: boolean
}

export interface GetThreadParams {
  thread_id: string
  email: string
  download_attachments?: boolean
}

export interface GetFullInboxParams {
  email: string
  max_results?: number
  query?: string
  download_attachments?: boolean
}

export const inboundService = {
  getInbox: ({ ...params }: GetInboxParams) =>
    runApiCall<InboxListResponse>({ method: "GET", url: "/inbox", params }),

  getMessage: ({ message_id, ...params }: GetMessageParams) =>
    runApiCall({
      method: "GET",
      url: `/inbox/message/${encodeURIComponent(message_id)}`,
      params,
    }),

  getFullInbox: (params: GetFullInboxParams) =>
    runApiCall<InboxFullResponse>({ method: "GET", url: "/inbox/full", params }),

  getThread: ({ thread_id, ...params }: GetThreadParams) =>
    runApiCall<InboxThreadResponse>({
      method: "GET",
      url: `/inbox/thread/${encodeURIComponent(thread_id)}`,
      params,
    }),

  downloadAttachmentUrl: (apiBaseUrl: string, email: string, filename: string) =>
    `${apiBaseUrl}/attachments/${encodeURIComponent(email)}/${encodeURIComponent(filename)}`,
}
