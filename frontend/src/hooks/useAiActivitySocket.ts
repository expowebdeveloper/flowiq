import { useEffect, useRef } from "react"
import { API_BASE_URL } from "@/services/apiClient"
import type { AiActivityEvent } from "@/services/aiActivityService"

/**
 * Read-only live feed of AI background-processing events — modeled on
 * useChatSocket, but the client never sends anything back over this socket,
 * it only receives broadcasts (see WS /agent-activity/ws, backend/
 * agent_activity/routes.py).
 *
 * onConnectionChange fires as soon as the socket itself opens/closes —
 * distinct from onEvent, which only fires when an actual activity event
 * arrives. Background activity can be infrequent (e.g. mailbox polling with
 * nothing new to report emits nothing at all), so a "Live" indicator driven
 * off onEvent alone would stay stuck on "Connecting…" indefinitely even
 * though the socket connected fine.
 */
export function useAiActivitySocket(
  token: string | null,
  onEvent: (event: AiActivityEvent) => void,
  onConnectionChange?: (connected: boolean) => void,
) {
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent
  const onConnectionChangeRef = useRef(onConnectionChange)
  onConnectionChangeRef.current = onConnectionChange

  useEffect(() => {
    if (!token) return

    const wsUrl = new URL(API_BASE_URL)
    wsUrl.protocol = wsUrl.protocol === "https:" ? "wss:" : "ws:"
    wsUrl.pathname = "/agent-activity/ws"
    wsUrl.searchParams.set("token", token)

    const socket = new WebSocket(wsUrl.toString())

    socket.onopen = () => {
      onConnectionChangeRef.current?.(true)
    }

    socket.onmessage = (event) => {
      onEventRef.current(JSON.parse(event.data) as AiActivityEvent)
    }

    socket.onclose = () => {
      onConnectionChangeRef.current?.(false)
    }

    return () => {
      socket.close()
    }
  }, [token])
}
