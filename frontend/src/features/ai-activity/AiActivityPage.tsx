import { useEffect, useRef, useState } from "react"
import {
  AlertCircle,
  AlertTriangle,
  Banknote,
  Bot,
  CheckCircle2,
  ChevronDown,
  Landmark,
  Loader2,
  Mail,
  Radio,
  ScanLine,
} from "lucide-react"
import { PageHeader } from "@/components/shared/PageHeader"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { useAuth } from "@/contexts/AuthContext"
import { useAiActivitySocket } from "@/hooks/useAiActivitySocket"
import { loanApplyService } from "@/services/loanApplyService"
import { loanTypeLabel } from "@/features/loans/loanTypeMeta"
import { aiActivityService, type AiActivityEvent, type AiActivitySource } from "@/services/aiActivityService"
import { cn } from "@/lib/utils"
import { PipelineStepper, deriveStepStates } from "./PipelineStepper"
import { groupEventsByApplicant, findApplicantIssue, type ApplicantGroup } from "./applicantGrouping"

const MAX_EVENTS_SHOWN = 200
const RECENT_EVENTS_COLLAPSED = 3

const SOURCE_META: Record<AiActivitySource, { label: string; icon: typeof Bot }> = {
  mailbox_poll: { label: "Mailbox polling", icon: Mail },
  document_processing: { label: "Document processing", icon: ScanLine },
  email_agent: { label: "AI email agent", icon: Bot },
  bank_notify: { label: "Bank notifications", icon: Landmark },
  bank_decision: { label: "Bank decision", icon: Banknote },
}

const STATUS_META: Record<
  AiActivityEvent["status"],
  { variant: "secondary" | "warning" | "success" | "destructive"; icon: typeof CheckCircle2 }
> = {
  started: { variant: "secondary", icon: Loader2 },
  info: { variant: "warning", icon: AlertCircle },
  success: { variant: "success", icon: CheckCircle2 },
  error: { variant: "destructive", icon: AlertCircle },
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "medium" })
  } catch {
    return iso
  }
}

export function AiActivityPage() {
  const { token } = useAuth()
  const [events, setEvents] = useState<AiActivityEvent[] | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isLive, setIsLive] = useState(false)
  const seenIds = useRef(new Set<string>())

  useEffect(() => {
    let cancelled = false
    aiActivityService.list(MAX_EVENTS_SHOWN).then((result) => {
      if (cancelled) return
      if (result.ok && result.data) {
        result.data.events.forEach((e) => seenIds.current.add(e.id))
        setEvents(result.data.events)
      } else {
        setErrorMessage(result.errorMessage ?? "Failed to load activity")
      }
    })
    return () => {
      cancelled = true
    }
  }, [])

  useAiActivitySocket(
    token,
    (incoming) => {
      if (seenIds.current.has(incoming.id)) return
      seenIds.current.add(incoming.id)
      setEvents((prev) => [incoming, ...(prev ?? [])].slice(0, MAX_EVENTS_SHOWN))
    },
    setIsLive,
  )

  const { groups, unscoped } = events ? groupEventsByApplicant(events) : { groups: [], unscoped: [] }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6 flex items-start justify-between gap-4">
        <PageHeader
          title="AI Activity"
          description="Real-time view of AI background processing, grouped by applicant."
        />
        <span
          className={cn(
            "mt-1 inline-flex shrink-0 items-center gap-1.5 rounded-md border px-2 py-1 text-xs font-medium",
            isLive
              ? "border-success/30 bg-success/10 text-success"
              : "border-border bg-muted/30 text-muted-foreground",
          )}
        >
          <Radio className={cn("size-3", isLive && "animate-pulse")} />
          {isLive ? "Live" : "Connecting…"}
        </span>
      </div>

      {events === null && !errorMessage && (
        <div className="flex items-center justify-center gap-2 py-16 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" /> Loading activity…
        </div>
      )}

      {errorMessage && <p className="text-sm text-destructive">{errorMessage}</p>}

      {events && events.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-2 py-16 text-sm text-muted-foreground">
          <Bot className="size-8 opacity-40" />
          No AI activity recorded yet.
        </div>
      )}

      {events && groups.length > 0 && (
        <div className="space-y-4">
          {groups.map((group) => (
            <ApplicantPipelineCard key={group.submissionId} group={group} />
          ))}
        </div>
      )}

      {events && unscoped.length > 0 && (
        <div className="mt-4 space-y-2">
          <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">System activity</h3>
          {unscoped.slice(0, RECENT_EVENTS_COLLAPSED).map((event) => (
            <ActivityEventRow key={event.id} event={event} />
          ))}
        </div>
      )}
    </div>
  )
}

function ApplicantPipelineCard({ group }: { group: ApplicantGroup }) {
  const [expanded, setExpanded] = useState(false)
  const [applicantLabel, setApplicantLabel] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    loanApplyService.getById(group.submissionId).then((result) => {
      if (cancelled) return
      if (result.ok && result.data) {
        const name = `${result.data.first_name} ${result.data.last_name}`.trim()
        setApplicantLabel(`${name} · ${loanTypeLabel(result.data.loan_type)}`)
      }
    })
    return () => {
      cancelled = true
    }
  }, [group.submissionId])

  const states = deriveStepStates(group.events)
  const issue = findApplicantIssue(group.events)
  const visibleEvents = expanded ? group.events : group.events.slice(0, RECENT_EVENTS_COLLAPSED)
  const hiddenCount = group.events.length - visibleEvents.length

  return (
    <Card className="overflow-hidden">
      <CardContent className="p-6">
        <div className="mb-6 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
          <h3 className="text-sm font-semibold">{applicantLabel ?? "Applicant"}</h3>
          <span className="text-xs text-muted-foreground">Last updated {formatDate(group.latestAt)}</span>
        </div>

        <PipelineStepper states={states} />

        {issue && (
          <div className="mt-6 flex items-start gap-2.5 rounded-lg border border-warning/30 bg-warning/10 px-3.5 py-3">
            <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warning" />
            <p className="text-sm text-warning">{issue.message}</p>
          </div>
        )}

        <div className="mt-6 space-y-2">
          {visibleEvents.map((event) => (
            <ActivityEventRow key={event.id} event={event} />
          ))}
          {hiddenCount > 0 && (
            <button
              type="button"
              onClick={() => setExpanded(true)}
              className="flex w-full items-center justify-center gap-1 rounded-md py-1.5 text-xs text-muted-foreground hover:text-foreground"
            >
              <ChevronDown className="size-3.5" />
              Show {hiddenCount} more event{hiddenCount === 1 ? "" : "s"}
            </button>
          )}
          {expanded && group.events.length > RECENT_EVENTS_COLLAPSED && (
            <button
              type="button"
              onClick={() => setExpanded(false)}
              className="flex w-full items-center justify-center gap-1 rounded-md py-1.5 text-xs text-muted-foreground hover:text-foreground"
            >
              Show less
            </button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function ActivityEventRow({ event }: { event: AiActivityEvent }) {
  const source = SOURCE_META[event.source] ?? { label: event.source, icon: Bot }
  const status = STATUS_META[event.status] ?? STATUS_META.info
  const SourceIcon = source.icon
  const StatusIcon = status.icon

  return (
    <div className="flex items-start gap-3 rounded-lg border border-border bg-muted/20 p-3">
      <span
        className={cn(
          "mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full border",
          status.variant === "success" && "border-success/30 bg-success/10 text-success",
          status.variant === "destructive" && "border-destructive/30 bg-destructive/10 text-destructive",
          status.variant === "warning" && "border-warning/30 bg-warning/10 text-warning",
          status.variant === "secondary" && "border-border bg-muted/30 text-muted-foreground",
        )}
      >
        <SourceIcon className="size-3.5" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
          <div className="flex items-center gap-2">
            <Badge variant="outline">{source.label}</Badge>
            <Badge variant={status.variant}>
              <StatusIcon className={cn("mr-1 size-3", event.status === "started" && "animate-spin")} />
              {event.status}
            </Badge>
          </div>
          <span className="text-xs text-muted-foreground">{formatDate(event.created_at)}</span>
        </div>
        <p className="mt-1.5 text-sm">{event.message}</p>
      </div>
    </div>
  )
}
