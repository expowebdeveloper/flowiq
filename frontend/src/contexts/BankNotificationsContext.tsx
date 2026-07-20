import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react"
import { useAuth } from "@/contexts/AuthContext"
import {
  bankNotificationService,
  type BankNotification,
  type BankDecisionStatus,
} from "@/services/bankNotificationService"

const POLL_INTERVAL_MS = 30_000

interface BankNotificationsContextValue {
  notifications: BankNotification[]
  unreadCount: number
  loading: boolean
  markRead: (id: string) => void
  recordDecision: (
    id: string,
    status: BankDecisionStatus,
    remarks: string | null,
  ) => Promise<{ ok: boolean; errorMessage?: string }>
}

const BankNotificationsContext = createContext<BankNotificationsContextValue | null>(null)

/**
 * Polls GET /bank-notifications for bank-role users only (no-op/empty for
 * everyone else) so the unread count is available wherever it's needed —
 * currently the sidebar badge and the full notifications list page — without
 * each of those independently polling the same endpoint.
 */
export function BankNotificationsProvider({ children }: { children: ReactNode }) {
  const { user, isAuthenticated } = useAuth()
  const [notifications, setNotifications] = useState<BankNotification[]>([])
  const [loading, setLoading] = useState(true)

  const isBank = isAuthenticated && user?.role === "bank"

  const refresh = useCallback(() => {
    if (!isBank) return
    bankNotificationService.list().then((res) => {
      if (res.ok && res.data) {
        setNotifications(res.data.notifications)
      }
      setLoading(false)
    })
  }, [isBank])

  useEffect(() => {
    if (!isBank) {
      setNotifications([])
      setLoading(false)
      return
    }
    refresh()
    const interval = setInterval(refresh, POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [isBank, refresh])

  function markRead(id: string) {
    // Optimistic — the count should disappear the moment the bank reads it,
    // not after the round trip completes. Reverted if the request fails.
    setNotifications((prev) =>
      prev.map((n) => (n.id === id && !n.read_at ? { ...n, read_at: new Date().toISOString() } : n)),
    )
    bankNotificationService.markRead(id).then((res) => {
      if (!res.ok) refresh()
    })
  }

  async function recordDecision(id: string, status: BankDecisionStatus, remarks: string | null) {
    const res = await bankNotificationService.recordDecision(id, status, remarks)
    if (res.ok && res.data) {
      const decision = res.data
      setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, decision } : n)))
      return { ok: true }
    }
    return { ok: false, errorMessage: res.errorMessage ?? "Failed to record decision" }
  }

  const unreadCount = notifications.filter((n) => !n.read_at).length

  return (
    <BankNotificationsContext.Provider
      value={{ notifications, unreadCount, loading, markRead, recordDecision }}
    >
      {children}
    </BankNotificationsContext.Provider>
  )
}

export function useBankNotifications() {
  const ctx = useContext(BankNotificationsContext)
  if (!ctx) throw new Error("useBankNotifications must be used within BankNotificationsProvider")
  return ctx
}
