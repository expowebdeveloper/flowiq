import { runApiCall } from "./apiClient"
import type { ChatMessage, ChatUser } from "@/types/api"

export const chatService = {
  listUsers: () => runApiCall<ChatUser[]>({ method: "GET", url: "/chat/users" }),

  getConversation: (otherUserId: string) =>
    runApiCall<ChatMessage[]>({
      method: "GET",
      url: `/chat/messages/${encodeURIComponent(otherUserId)}`,
    }),
}
