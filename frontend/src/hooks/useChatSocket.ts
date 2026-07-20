import { useCallback, useEffect, useRef } from "react"
import { API_BASE_URL } from "@/services/apiClient"
import type { ChatMessage } from "@/types/api"

/**
 * One persistent WebSocket for the whole chat feature (not per-conversation) —
 * the backend routes incoming messages to whichever recipient is connected,
 * so a single socket receives messages from any sender.
 */
export function useChatSocket(token: string | null, onMessage: (message: ChatMessage) => void) {
  const socketRef = useRef<WebSocket | null>(null)
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  useEffect(() => {
    if (!token) return

    const wsUrl = new URL(API_BASE_URL)
    wsUrl.protocol = wsUrl.protocol === "https:" ? "wss:" : "ws:"
    wsUrl.pathname = "/chat/ws"
    wsUrl.searchParams.set("token", token)

    const socket = new WebSocket(wsUrl.toString())
    socketRef.current = socket

    socket.onmessage = (event) => {
      onMessageRef.current(JSON.parse(event.data) as ChatMessage)
    }

    return () => {
      socket.close()
      socketRef.current = null
    }
  }, [token])

  const sendMessage = useCallback((recipientId: string, body: string) => {
    socketRef.current?.send(JSON.stringify({ recipient_id: recipientId, body }))
  }, [])

  return { sendMessage }
}
