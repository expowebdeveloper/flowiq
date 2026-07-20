import { Check, Loader2, Mail, ScanLine, Landmark, Gavel } from "lucide-react"
import { cn } from "@/lib/utils"
import type { AiActivityEvent } from "@/services/aiActivityService"

export type StepState = "done" | "active" | "pending"

interface StepDef {
  key: string
  label: string
  description: string
  icon: typeof Mail
}

const STEP_DEFS: StepDef[] = [
  { key: "inbound", label: "Inbound Parse", description: "Applicant email received", icon: Mail },
  { key: "verification", label: "Verification", description: "Documents checked", icon: ScanLine },
  { key: "bank_sync", label: "Bank Syncing", description: "Sent to partner banks", icon: Landmark },
  { key: "decision", label: "Final Decision", description: "Bank outcome relayed", icon: Gavel },
]

/**
 * Derives each of the 4 pipeline steps' state from one applicant's
 * AgentActivityEvent rows. There's no single "inbound" event type
 * (mailbox_poll carries no submission_id), so step 1 is treated as done the
 * moment any submission-scoped event exists, since document processing can
 * only have started after the applicant's reply was parsed.
 */
export function deriveStepStates(eventsNewestFirst: AiActivityEvent[]): StepState[] {
  if (eventsNewestFirst.length === 0) return ["pending", "pending", "pending", "pending"]

  const docEvents = eventsNewestFirst.filter((e) => e.source === "document_processing")
  const bankNotifyEvents = eventsNewestFirst.filter((e) => e.source === "bank_notify")
  const bankDecisionEvents = eventsNewestFirst.filter((e) => e.source === "bank_decision")
  const emailEvents = eventsNewestFirst.filter((e) => e.source === "email_agent")

  const inbound: StepState = "done"

  const docsVerified = docEvents.some((e) => e.status === "success")
  const docsStarted = docEvents.length > 0
  const verification: StepState = docsVerified ? "done" : docsStarted ? "active" : "pending"

  const banksNotified = bankNotifyEvents.some((e) => e.status === "success")
  const bankSync: StepState = banksNotified ? "done" : verification === "done" ? "active" : "pending"

  const decisionStarted = bankDecisionEvents.some((e) => e.status === "started")
  const decisionEmailed = decisionStarted && emailEvents.some((e) => e.status === "success")
  const decision: StepState = decisionEmailed ? "done" : decisionStarted ? "active" : "pending"

  return [inbound, verification, bankSync, decision]
}

export function PipelineStepper({ states }: { states: StepState[] }) {
  return (
    <div className="grid grid-cols-4 gap-0">
      {STEP_DEFS.map((step, i) => {
        const state = states[i]
        const isLast = i === STEP_DEFS.length - 1
        return (
          <div key={step.key} className="relative flex flex-col items-center px-2 text-center">
            {!isLast && (
              <div
                className={cn(
                  "absolute left-1/2 top-6 h-0.5 w-full -translate-y-1/2",
                  states[i + 1] !== "pending" || state === "done" ? "bg-success" : "bg-border",
                )}
                aria-hidden
              />
            )}
            <StepIcon state={state} icon={step.icon} />
            <p className={cn("mt-3 text-sm font-medium", state === "pending" && "text-muted-foreground")}>
              {step.label}
            </p>
            <p className="mt-0.5 text-xs text-muted-foreground">{step.description}</p>
          </div>
        )
      })}
    </div>
  )
}

function StepIcon({ state, icon: Icon }: { state: StepState; icon: typeof Mail }) {
  return (
    <span
      className={cn(
        "relative z-10 flex size-12 shrink-0 items-center justify-center rounded-full border-2 bg-card transition-colors",
        state === "done" && "border-success bg-success text-success-foreground",
        state === "active" && "border-primary text-primary ring-4 ring-primary/15",
        state === "pending" && "border-border text-muted-foreground",
      )}
    >
      {state === "active" && (
        <span className="absolute inset-0 animate-ping rounded-full bg-primary/30" aria-hidden />
      )}
      {state === "done" ? (
        <Check className="size-5" />
      ) : state === "active" ? (
        <Loader2 className="size-5 animate-spin" />
      ) : (
        <Icon className="size-5" />
      )}
    </span>
  )
}
