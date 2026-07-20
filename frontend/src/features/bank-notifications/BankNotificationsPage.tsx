import { useState } from "react"
import { Bell, Check, FileText, Loader2, X } from "lucide-react"
import { PageHeader } from "@/components/shared/PageHeader"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { useBankNotifications } from "@/contexts/BankNotificationsContext"
import { loanTypeLabel } from "@/features/loans/loanTypeMeta"
import { bankNotificationService } from "@/services/bankNotificationService"
import type { BankNotification, BankDecisionStatus } from "@/services/bankNotificationService"

const DECISION_META: Record<
  BankDecisionStatus,
  { label: string; variant: "success" | "warning" | "destructive"; prompt: string; placeholder: string }
> = {
  rejected: {
    label: "Rejected",
    variant: "destructive",
    prompt: "Reject application",
    placeholder: "Reason for rejection (optional)",
  },
  offer: {
    label: "Offer made",
    variant: "success",
    prompt: "Make an offer",
    placeholder: "Offer terms — amount, interest rate, tenure (optional)",
  },
  offer_more_documents: {
    label: "More documents requested",
    variant: "warning",
    prompt: "Request more documents",
    placeholder: "Which documents/information are needed (optional)",
  },
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(amount)
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })
  } catch {
    return iso
  }
}

export function BankNotificationsPage() {
  const { notifications, loading, markRead } = useBankNotifications()

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title="Notifications" description="New leads matching the loan types you offer." />

      {loading && (
        <div className="flex items-center justify-center gap-2 py-16 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" /> Loading notifications…
        </div>
      )}

      {!loading && notifications.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-2 py-16 text-sm text-muted-foreground">
          <Bell className="size-8 opacity-40" />
          No notifications yet.
        </div>
      )}

      {!loading && notifications.length > 0 && (
        <div className="space-y-2">
          {notifications.map((n) => (
            <NotificationCard key={n.id} notification={n} onRead={() => markRead(n.id)} />
          ))}
        </div>
      )}
    </div>
  )
}

function NotificationCard({
  notification,
  onRead,
}: {
  notification: BankNotification
  onRead: () => void
}) {
  const { recordDecision } = useBankNotifications()
  const isUnread = !notification.read_at
  const [isLoadingPdf, setIsLoadingPdf] = useState(false)
  const [pdfError, setPdfError] = useState<string | null>(null)
  const [pendingStatus, setPendingStatus] = useState<BankDecisionStatus | null>(null)
  const [remarks, setRemarks] = useState("")
  const [isSubmittingDecision, setIsSubmittingDecision] = useState(false)
  const [decisionError, setDecisionError] = useState<string | null>(null)

  async function handleViewPdf(event: React.MouseEvent) {
    event.stopPropagation()
    setPdfError(null)
    setIsLoadingPdf(true)
    const result = await bankNotificationService.getPdf(notification.id)
    setIsLoadingPdf(false)
    if (result.ok && result.data) {
      const url = URL.createObjectURL(result.data)
      window.open(url, "_blank", "noopener,noreferrer")
      // Revoke once the new tab has had a chance to load the blob.
      setTimeout(() => URL.revokeObjectURL(url), 30_000)
      if (isUnread) onRead()
    } else {
      setPdfError(result.errorMessage ?? "Failed to load PDF")
    }
  }

  function openDecisionDialog(event: React.MouseEvent, status: BankDecisionStatus) {
    event.stopPropagation()
    setRemarks(notification.decision?.status === status ? notification.decision.remarks ?? "" : "")
    setDecisionError(null)
    setPendingStatus(status)
  }

  async function handleSubmitDecision() {
    if (!pendingStatus) return
    setIsSubmittingDecision(true)
    setDecisionError(null)
    const result = await recordDecision(notification.id, pendingStatus, remarks.trim() || null)
    setIsSubmittingDecision(false)
    if (result.ok) {
      setPendingStatus(null)
      if (isUnread) onRead()
    } else {
      setDecisionError(result.errorMessage ?? "Failed to record decision")
    }
  }

  return (
    <Card
      className={isUnread ? "border-primary/40 bg-primary/[0.03] transition-colors" : "transition-colors"}
    >
      <CardContent className="flex items-start gap-3 p-4">
        <button
          type="button"
          onClick={() => isUnread && onRead()}
          className="flex min-w-0 flex-1 items-start gap-3 text-left"
        >
          <span
            className={
              isUnread
                ? "mt-1.5 size-2 shrink-0 rounded-full bg-primary"
                : "mt-1.5 size-2 shrink-0 rounded-full bg-transparent"
            }
            aria-hidden
          />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
              <span className="font-medium">{notification.applicant_name ?? "Unknown applicant"}</span>
              <span className="text-xs text-muted-foreground">{formatDate(notification.created_at)}</span>
            </div>
            <p className="mt-0.5 text-sm text-muted-foreground">{notification.applicant_email}</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              {notification.loan_type && (
                <Badge variant="outline">{loanTypeLabel(notification.loan_type)}</Badge>
              )}
              {notification.loan_amount != null && (
                <span className="text-xs text-muted-foreground">
                  {formatCurrency(notification.loan_amount)}
                </span>
              )}
              {notification.fico_score != null && (
                <span className="text-xs text-muted-foreground">FICO {notification.fico_score}</span>
              )}
              {notification.decision && (
                <Badge variant={DECISION_META[notification.decision.status].variant}>
                  {DECISION_META[notification.decision.status].label}
                </Badge>
              )}
            </div>
            {pdfError && <p className="mt-1 text-xs text-destructive">{pdfError}</p>}
          </div>
        </button>
        <div className="flex shrink-0 flex-col items-stretch gap-1.5">
          <Button type="button" variant="outline" size="sm" disabled={isLoadingPdf} onClick={handleViewPdf}>
            {isLoadingPdf ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <FileText className="size-4" />
            )}
            View PDF
          </Button>
          <div className="flex gap-1.5">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="flex-1 text-destructive hover:text-destructive"
              onClick={(e) => openDecisionDialog(e, "rejected")}
            >
              <X className="size-4" />
              Reject
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="flex-1 text-success hover:text-success"
              onClick={(e) => openDecisionDialog(e, "offer")}
            >
              <Check className="size-4" />
              Offer
            </Button>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={(e) => openDecisionDialog(e, "offer_more_documents")}
          >
            Offer — need documents
          </Button>
        </div>
      </CardContent>

      <Dialog open={pendingStatus !== null} onOpenChange={(open) => !open && setPendingStatus(null)}>
        <DialogContent onClick={(e) => e.stopPropagation()}>
          {pendingStatus && (
            <>
              <DialogHeader>
                <DialogTitle>{DECISION_META[pendingStatus].prompt}</DialogTitle>
                <DialogDescription>
                  {notification.applicant_name ?? "This applicant"} will be emailed automatically once you
                  confirm.
                </DialogDescription>
              </DialogHeader>
              <Textarea
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                placeholder={DECISION_META[pendingStatus].placeholder}
                rows={4}
              />
              {decisionError && <p className="text-xs text-destructive">{decisionError}</p>}
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setPendingStatus(null)}>
                  Cancel
                </Button>
                <Button type="button" onClick={handleSubmitDecision} disabled={isSubmittingDecision}>
                  {isSubmittingDecision && <Loader2 className="size-4 animate-spin" />}
                  Confirm
                </Button>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </Card>
  )
}
