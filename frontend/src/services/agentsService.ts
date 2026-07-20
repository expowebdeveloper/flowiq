import { runApiCall } from "./apiClient"
import type { AgentRunRequest, AgentRunResponse, AgentStatusResponse } from "@/types/api"

export const agentsService = {
  run: (payload: AgentRunRequest) =>
    runApiCall<AgentRunResponse>({ method: "POST", url: "/agent/run", data: payload }),

  status: (taskId: string) =>
    runApiCall<AgentStatusResponse>({
      method: "GET",
      url: `/agent/status/${encodeURIComponent(taskId)}`,
    }),
}
