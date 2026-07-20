import { runApiCall } from "./apiClient"
import type { SendEmailRequest, SendEmailResponse } from "@/types/api"

export const outboundService = {
  send: (payload: SendEmailRequest) =>
    runApiCall<SendEmailResponse>({ method: "POST", url: "/send", data: payload }),
}
