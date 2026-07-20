import { useEffect, useMemo, useState } from "react"
import { useSearchParams } from "react-router-dom"
import {
  AlertTriangle,
  ArrowLeft,
  Banknote,
  Cake,
  Calendar,
  CheckCircle2,
  ChevronDown,
  CreditCard,
  FileText,
  FileWarning,
  Landmark,
  Loader2,
  Mail,
  MapPin,
  Paperclip,
  Phone,
  ScanLine,
  Send,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  User,
  X,
} from "lucide-react"
import { PageHeader } from "@/components/shared/PageHeader"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { loanTypeLabel } from "@/features/loans/loanTypeMeta"
import { HOME_LOAN_FIELD_LABELS } from "@/features/loan-apply/HomeLoanDetailsStep"
import { PERSONAL_LOAN_FIELD_LABELS } from "@/features/loan-apply/PersonalLoanDetailsStep"
import { CAR_LOAN_FIELD_LABELS } from "@/features/loan-apply/CarLoanDetailsStep"
import { EDUCATION_LOAN_FIELD_LABELS } from "@/features/loan-apply/EducationLoanDetailsStep"
import { GOLD_LOAN_FIELD_LABELS } from "@/features/loan-apply/GoldLoanDetailsStep"
import {
  loanApplyService,
  type LeadActivityEvent,
  type LoanApplyResult,
  type LoanRequirement,
} from "@/services/loanApplyService"
import { aiActivityService, type AiActivityEvent } from "@/services/aiActivityService"
import { PipelineStepper, deriveStepStates } from "@/features/ai-activity/PipelineStepper"
import { findApplicantIssue } from "@/features/ai-activity/applicantGrouping"
import { LEAD_STAGE_DEFS, stageOf, type LeadStageKey } from "@/features/leads/leadStage"

// Merged label lookup across every loan type's dedicated details form — a
// lead's extra_loan_details keys only ever come from whichever ONE loan
// type it was submitted under, so key collisions across the merge (none
// currently exist) would just mean the last map wins for that key.
const ALL_LOAN_DETAIL_FIELD_LABELS: Record<string, string> = {
  ...HOME_LOAN_FIELD_LABELS,
  ...PERSONAL_LOAN_FIELD_LABELS,
  ...CAR_LOAN_FIELD_LABELS,
  ...EDUCATION_LOAN_FIELD_LABELS,
  ...GOLD_LOAN_FIELD_LABELS,
}

const LOAN_TYPE_TO_CATEGORY_KEY: Record<string, string> = {
  home_loan: "Home Loan",
  education_loan: "Education Loan",
  personal_loan: "Personal Loan",
  car_loan: "Vehicle Loan",
  gold_loan: "Gold Loan",
}

const DOCUMENTS_STATUS_META: Record<string, { label: string; variant: "secondary" | "warning" | "success" }> = {
  awaiting_documents: { label: "Awaiting documents", variant: "secondary" },
  documents_incomplete: { label: "Documents incomplete", variant: "warning" },
  documents_complete: { label: "Documents complete", variant: "success" },
}

const BANK_DECISION_META: Record<string, { label: string; variant: "destructive" | "success" | "warning" }> = {
  rejected: { label: "rejected the application", variant: "destructive" },
  offer: { label: "made an offer", variant: "success" },
  offer_more_documents: { label: "requested more documents", variant: "warning" },
}

const BANK_DECISION_BADGE_META: Record<string, { label: string; variant: "destructive" | "success" | "warning" }> = {
  rejected: { label: "Rejected", variant: "destructive" },
  offer: { label: "Offer made", variant: "success" },
  offer_more_documents: { label: "More documents needed", variant: "warning" },
}

const EXTRACTED_FIELD_LABELS: Record<string, string> = {
  gold_weight_grams: "Gold weight (grams)",
  gold_purity_carats: "Gold purity",
  property_value: "Property value",
  monthly_income: "Monthly income",
}

const EXTRACTED_CURRENCY_FIELDS = new Set([
  "property_value",
  "monthly_income",
  "annual_income",
  "monthly_debt_payments",
  "existing_loan_emi_amount",
  "checking_account_balance",
  "savings_account_balance",
  "purchase_price",
  "down_payment_amount",
])

function formatExtractedValue(key: string, rawValue: string): string {
  if (EXTRACTED_CURRENCY_FIELDS.has(key)) {
    const n = Number(rawValue)
    if (!isNaN(n) && rawValue.trim() !== "") {
      return formatCurrency(n)
    }
  }
  return rawValue
}

/** Shows only the last 4 digits of an SSN (e.g. "•••-••-6789") — a lead-management list view has no need to display the full number even though it's stored for the actual application. */
function maskSsn(ssn: string): string {
  const digits = ssn.replace(/\D/g, "")
  if (digits.length < 4) return "•••-••-••••"
  return `•••-••-${digits.slice(-4)}`
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    })
  } catch {
    return iso
  }
}

function formatDateMs(ms: number): string {
  try {
    return new Date(ms).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    })
  } catch {
    return String(ms)
  }
}

/** First plain-text line of an email address like "Jane Doe <jane@x.com>" — used so the timeline reads names, not raw headers. */
function displayName(addressHeader: string): string {
  const match = addressHeader.match(/^([^<]+)</)
  return (match ? match[1] : addressHeader).trim() || addressHeader
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(amount)
}

function initials(firstName: string, lastName: string): string {
  return `${firstName?.[0] ?? ""}${lastName?.[0] ?? ""}`.toUpperCase()
}

const LEAD_STAGE_KEYS = new Set(LEAD_STAGE_DEFS.map((s) => s.key))

function isLeadStageKey(value: string | null): value is LeadStageKey {
  return value !== null && LEAD_STAGE_KEYS.has(value as LeadStageKey)
}

export function LeadsPage() {
  const [leads, setLeads] = useState<LoanApplyResult[] | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [requirements, setRequirements] = useState<Record<string, LoanRequirement>>({})
  const [searchParams, setSearchParams] = useSearchParams()

  const stageParam = searchParams.get("stage")
  const activeStage = isLeadStageKey(stageParam) ? stageParam : null

  useEffect(() => {
    loanApplyService.list().then((res) => {
      if (res.ok && res.data) {
        setLeads(res.data)
      } else {
        setErrorMessage(res.errorMessage ?? "Failed to load leads")
      }
    })
    loanApplyService.getRequirements().then((res) => {
      if (res.ok && res.data) setRequirements(res.data)
    })
  }, [])

  const filteredLeads = useMemo(() => {
    if (!leads) return leads
    if (!activeStage) return leads
    return leads.filter((lead) => stageOf(lead) === activeStage)
  }, [leads, activeStage])

  const selectedLead = leads?.find((l) => l.id === selectedId) ?? null

  if (selectedLead) {
    return (
      <LeadDetail
        lead={selectedLead}
        requirements={requirements}
        onBack={() => setSelectedId(null)}
      />
    )
  }

  const activeStageDef = activeStage ? LEAD_STAGE_DEFS.find((s) => s.key === activeStage) : null

  return (
    <div>
      <PageHeader title="Leads" description="Applicants who submitted the loan application form." />

      {activeStageDef && (
        <div className="mb-4 flex items-center gap-2">
          <Badge
            variant={activeStage === "reject" ? "destructive" : "secondary"}
            className="flex items-center gap-1.5 py-1 pl-2.5 pr-1.5 text-xs"
          >
            Stage: {activeStageDef.label}
            <button
              type="button"
              onClick={() => setSearchParams((prev) => {
                const next = new URLSearchParams(prev)
                next.delete("stage")
                return next
              })}
              className="rounded-full p-0.5 hover:bg-black/10"
              aria-label="Clear stage filter"
            >
              <X className="size-3" />
            </button>
          </Badge>
          <span className="text-xs text-muted-foreground">{activeStageDef.description}</span>
        </div>
      )}

      {errorMessage && (
        <div className="mb-4 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
          {errorMessage}
        </div>
      )}

      {!leads && !errorMessage && (
        <div className="flex items-center justify-center gap-2 py-16 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" /> Loading leads…
        </div>
      )}

      {leads && leads.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-2 py-16 text-sm text-muted-foreground">
          <User className="size-8 opacity-40" />
          No leads yet.
        </div>
      )}

      {leads && leads.length > 0 && filteredLeads && filteredLeads.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-2 py-16 text-sm text-muted-foreground">
          <User className="size-8 opacity-40" />
          No leads in this stage.
        </div>
      )}

      {filteredLeads && filteredLeads.length > 0 && (
        <Card>
          <CardContent className="p-0">
            <div className="divide-y divide-border">
              {filteredLeads.map((lead) => {
                const statusMeta =
                  DOCUMENTS_STATUS_META[lead.documents_status] ?? DOCUMENTS_STATUS_META.awaiting_documents
                const rejections =
                  activeStage === "reject"
                    ? lead.bank_decisions.filter((d) => d.status === "rejected")
                    : []
                return (
                  <div key={lead.id} className="divide-y divide-border">
                    <button
                      onClick={() => setSelectedId(lead.id)}
                      className="flex w-full items-center gap-4 px-4 py-3 text-left transition-colors hover:bg-accent/50"
                    >
                      <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary/15 text-sm font-semibold text-primary">
                        {initials(lead.first_name, lead.last_name)}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="truncate text-sm font-medium">
                            {lead.first_name} {lead.last_name}
                          </span>
                          <Badge variant="outline" className="shrink-0">
                            {loanTypeLabel(lead.loan_type)}
                          </Badge>
                        </div>
                        <div className="truncate text-xs text-muted-foreground">{lead.email}</div>
                      </div>
                      <div className="hidden shrink-0 text-right text-sm sm:block">
                        {formatCurrency(lead.loan_amount)}
                      </div>
                      {lead.bank_decisions.length > 0 && (
                        <Badge
                          variant={
                            (BANK_DECISION_BADGE_META[lead.bank_decisions[0].status] ??
                              BANK_DECISION_BADGE_META.offer_more_documents).variant
                          }
                          className="hidden shrink-0 lg:inline-flex"
                        >
                          {(BANK_DECISION_BADGE_META[lead.bank_decisions[0].status] ??
                            BANK_DECISION_BADGE_META.offer_more_documents).label}
                        </Badge>
                      )}
                      <Badge variant={statusMeta.variant} className="shrink-0">
                        {statusMeta.label}
                      </Badge>
                      <div className="hidden shrink-0 text-xs text-muted-foreground md:block">
                        {formatDate(lead.created_at)}
                      </div>
                    </button>

                    {rejections.length > 0 && (
                      <div className="space-y-2 bg-destructive/5 px-4 py-3 pl-[68px]">
                        {rejections.map((decision) => (
                          <div key={`${decision.bank_name}-${decision.decided_at}`} className="text-sm">
                            <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                              <span className="font-medium text-destructive">{decision.bank_name} rejected</span>
                              <span className="text-xs text-muted-foreground">{formatDate(decision.decided_at)}</span>
                            </div>
                            <p className="mt-0.5 text-muted-foreground">
                              {decision.remarks || "No reason provided by the bank."}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function InfoRow({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof User
  label: string
  value: string
}) {
  return (
    <div className="flex items-start gap-3">
      <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
      <div className="min-w-0">
        <div className="text-xs text-muted-foreground">{label}</div>
        <div className="truncate text-sm font-medium">{value}</div>
      </div>
    </div>
  )
}

function LeadDetail({
  lead,
  requirements,
  onBack,
}: {
  lead: LoanApplyResult
  requirements: Record<string, LoanRequirement>
  onBack: () => void
}) {
  const statusMeta = DOCUMENTS_STATUS_META[lead.documents_status] ?? DOCUMENTS_STATUS_META.awaiting_documents
  const categoryKey = LOAN_TYPE_TO_CATEGORY_KEY[lead.loan_type]
  const categoryFields = categoryKey ? requirements[categoryKey]?.mandatory_fields ?? [] : []
  const hasExtraDetails = lead.extra_loan_details && Object.keys(lead.extra_loan_details).length > 0

  const documentFieldEntries = Object.entries(lead.extracted_data ?? {}).filter(([, value]) => Boolean(value))
  const hasOcrData = documentFieldEntries.length > 0

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6 flex items-center gap-3">
        <Button variant="ghost" size="icon" className="size-8" onClick={onBack}>
          <ArrowLeft className="size-4" />
        </Button>
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">
            {lead.first_name} {lead.last_name}
          </h2>
          <p className="text-sm text-muted-foreground">{lead.email}</p>
        </div>
        <Badge variant={statusMeta.variant} className="ml-auto">
          {statusMeta.label}
        </Badge>
      </div>

      <div className="space-y-4">
        <LeadPipelineCard leadId={lead.id} />

        <Card>
          <CardContent className="grid gap-4 p-5 sm:grid-cols-2">
            <InfoRow icon={User} label="Full name" value={`${lead.first_name} ${lead.last_name}`} />
            <InfoRow icon={Mail} label="Email" value={lead.email} />
            {lead.phone_number && <InfoRow icon={Phone} label="Phone" value={lead.phone_number} />}
            {lead.date_of_birth && <InfoRow icon={Cake} label="Date of birth" value={lead.date_of_birth} />}
            {lead.ssn && <InfoRow icon={CreditCard} label="SSN" value={maskSsn(lead.ssn)} />}
            <InfoRow icon={User} label="Gender" value={lead.gender} />
            {lead.marital_status && (
              <InfoRow icon={User} label="Marital status" value={lead.marital_status} />
            )}
            {lead.current_address && (
              <InfoRow icon={MapPin} label="Current address" value={lead.current_address} />
            )}
            <InfoRow icon={MapPin} label="ZIP code" value={lead.zip_code} />
            <InfoRow icon={Banknote} label="Loan type" value={loanTypeLabel(lead.loan_type)} />
            <InfoRow icon={Banknote} label="Loan amount" value={formatCurrency(lead.loan_amount)} />
            <InfoRow icon={FileText} label="FICO score" value={String(lead.fico_score)} />
            <InfoRow icon={Calendar} label="Submitted" value={formatDate(lead.created_at)} />
          </CardContent>
        </Card>

        {hasExtraDetails && (
          <Card>
            <CardContent className="p-5">
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                {loanTypeLabel(lead.loan_type)} details
              </h3>
              <div className="grid gap-4 sm:grid-cols-2">
                {Object.entries(lead.extra_loan_details ?? {}).map(([key, value]) => {
                  const meta = categoryFields.find((f) => f.field === key)
                  const label = meta?.label ?? ALL_LOAN_DETAIL_FIELD_LABELS[key] ?? key.replace(/_/g, " ")
                  return (
                    <InfoRow
                      key={key}
                      icon={FileText}
                      label={label}
                      value={value ? formatExtractedValue(key, value) : "—"}
                    />
                  )
                })}
              </div>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardContent className="p-5">
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
              <ScanLine className="size-4" /> Extracted from documents (OCR)
            </h3>
            {hasOcrData ? (
              <div className="grid gap-4 sm:grid-cols-2">
                {documentFieldEntries.map(([key, value]) => (
                  <InfoRow
                    key={key}
                    icon={FileText}
                    label={EXTRACTED_FIELD_LABELS[key] ?? key.replace(/_/g, " ")}
                    value={formatExtractedValue(key, String(value))}
                  />
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                {lead.documents_status === "awaiting_documents"
                  ? "No documents received yet."
                  : "No details could be extracted from the documents received so far."}
              </p>
            )}
          </CardContent>
        </Card>

        {lead.bank_decisions.length > 0 && (
          <Card>
            <CardContent className="p-5">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                <Landmark className="size-4" /> Bank decisions
              </h3>
              <div className="space-y-2">
                {lead.bank_decisions.map((decision) => {
                  const meta =
                    BANK_DECISION_BADGE_META[decision.status] ?? BANK_DECISION_BADGE_META.offer_more_documents
                  return (
                    <div
                      key={`${decision.bank_name}-${decision.decided_at}`}
                      className="rounded-lg border border-border p-3"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
                        <span className="text-sm font-medium">{decision.bank_name}</span>
                        <div className="flex items-center gap-2">
                          <Badge variant={meta.variant}>{meta.label}</Badge>
                          <span className="text-xs text-muted-foreground">{formatDate(decision.decided_at)}</span>
                        </div>
                      </div>
                      {decision.remarks && (
                        <p className="mt-1.5 text-sm text-muted-foreground">{decision.remarks}</p>
                      )}
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        )}

        <ActivityLog leadId={lead.id} />
      </div>
    </div>
  )
}

function LeadPipelineCard({ leadId }: { leadId: string }) {
  const [events, setEvents] = useState<AiActivityEvent[] | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setEvents(null)
    setErrorMessage(null)
    aiActivityService.listForSubmission(leadId).then((result) => {
      if (cancelled) return
      if (result.ok && result.data) {
        setEvents(result.data.events)
      } else {
        setErrorMessage(result.errorMessage ?? "Failed to load pipeline status")
      }
    })
    return () => {
      cancelled = true
    }
  }, [leadId])

  return (
    <Card>
      <CardContent className="p-6">
        <h3 className="mb-6 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Pipeline status
        </h3>

        {errorMessage && <p className="text-sm text-destructive">{errorMessage}</p>}

        {!events && !errorMessage && (
          <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" /> Loading pipeline…
          </div>
        )}

        {events && (
          <>
            <PipelineStepper states={deriveStepStates(events)} />
            {(() => {
              const issue = findApplicantIssue(events)
              if (!issue) return null
              return (
                <div className="mt-6 flex items-start gap-2.5 rounded-lg border border-warning/30 bg-warning/10 px-3.5 py-3">
                  <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warning" />
                  <p className="text-sm text-warning">{issue.message}</p>
                </div>
              )
            })()}
          </>
        )}
      </CardContent>
    </Card>
  )
}

function ActivityLog({ leadId }: { leadId: string }) {
  const [events, setEvents] = useState<LeadActivityEvent[] | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    setEvents(null)
    setErrorMessage(null)
    loanApplyService.getActivity(leadId).then((res) => {
      if (res.ok && res.data) {
        setEvents(res.data.events)
      } else {
        setErrorMessage(res.errorMessage ?? "Failed to load activity log")
      }
    })
  }, [leadId])

  return (
    <Card>
      <CardContent className="p-5">
        <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          <Sparkles className="size-4" /> Activity log
        </h3>

        {errorMessage && (
          <p className="text-sm text-destructive">{errorMessage}</p>
        )}

        {!events && !errorMessage && (
          <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" /> Loading activity…
          </div>
        )}

        {events && events.length === 0 && (
          <p className="text-sm text-muted-foreground">No activity recorded yet.</p>
        )}

        {events && events.length > 0 && (
          <ol className="space-y-0">
            {events.map((event, i) => (
              <ActivityEventItem
                key={eventKey(event, i)}
                event={event}
                isLast={i === events.length - 1}
              />
            ))}
          </ol>
        )}
      </CardContent>
    </Card>
  )
}

function eventKey(event: LeadActivityEvent, index: number): string {
  if (event.type === "email") return event.gmail_message_id
  return `${event.type}-${index}`
}

function ActivityEventItem({ event, isLast }: { event: LeadActivityEvent; isLast: boolean }) {
  const [expanded, setExpanded] = useState(false)

  const { icon: Icon, iconClassName } = activityVisual(event)

  return (
    <li className="relative flex gap-3 pb-6 last:pb-0">
      {!isLast && (
        <span className="absolute left-[15px] top-8 bottom-0 w-px bg-border" aria-hidden />
      )}
      <span
        className={cn(
          "z-10 flex size-8 shrink-0 items-center justify-center rounded-full border",
          iconClassName,
        )}
      >
        <Icon className="size-4" />
      </span>

      <div className="min-w-0 flex-1 pt-0.5">
        {event.type === "lead_created" && (
          <>
            <p className="text-sm font-medium">Lead created</p>
            <p className="text-xs text-muted-foreground">
              Applied for {loanTypeLabel(event.loan_type)} · {formatDateMs(event.at_ms)}
            </p>
          </>
        )}

        {event.type === "documents_processed" && (
          <>
            <p className="text-sm font-medium">
              {event.documents_status === "documents_complete"
                ? "AI verified all required documents"
                : "AI processed documents — some still missing"}
            </p>
            <p className="text-xs text-muted-foreground">{formatDateMs(event.at_ms)}</p>
          </>
        )}

        {event.type === "bank_decision" && (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-medium">
                {event.bank_name} {BANK_DECISION_META[event.status]?.label ?? "updated the application"}
              </p>
              <Badge variant={BANK_DECISION_META[event.status]?.variant ?? "secondary"}>
                {BANK_DECISION_META[event.status]?.label ?? event.status}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">{formatDateMs(event.at_ms)}</p>
            {event.remarks && (
              <p className="mt-1 whitespace-pre-line rounded-md border border-border bg-muted/30 p-2 text-xs text-foreground/90">
                {event.remarks}
              </p>
            )}
          </>
        )}

        {event.type === "email" && (
          <div>
            <div className="flex flex-wrap items-baseline gap-x-2">
              <p className="text-sm font-medium">
                {event.direction === "outbound"
                  ? `AI sent an email to ${displayName(event.to)}`
                  : `${displayName(event.from)} replied`}
              </p>
              <span className="text-xs text-muted-foreground">
                {event.internal_date_ms ? formatDateMs(event.internal_date_ms) : event.date}
              </span>
            </div>
            <p className="mt-0.5 truncate text-xs text-muted-foreground">{event.subject}</p>

            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              className="mt-2 flex w-full items-start gap-2 rounded-md border border-border bg-muted/30 p-3 text-left text-sm hover:bg-muted/50"
            >
              <div className="min-w-0 flex-1">
                <p className={cn("whitespace-pre-line text-foreground/90", !expanded && "line-clamp-2")}>
                  {expanded ? event.body || event.snippet : event.snippet || event.body}
                </p>
                {event.attachments.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {event.attachments.map((filename) => (
                      <span
                        key={filename}
                        className="inline-flex items-center gap-1 rounded-md border border-border bg-background px-2 py-0.5 text-xs text-muted-foreground"
                      >
                        <Paperclip className="size-3" /> {filename}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <ChevronDown
                className={cn(
                  "mt-0.5 size-4 shrink-0 text-muted-foreground transition-transform",
                  expanded && "rotate-180",
                )}
              />
            </button>
          </div>
        )}
      </div>
    </li>
  )
}

function activityVisual(event: LeadActivityEvent): { icon: typeof User; iconClassName: string } {
  if (event.type === "lead_created") {
    return { icon: User, iconClassName: "border-primary/30 bg-primary/10 text-primary" }
  }
  if (event.type === "documents_processed") {
    return { icon: CheckCircle2, iconClassName: "border-success/30 bg-success/10 text-success" }
  }
  if (event.type === "bank_decision") {
    if (event.status === "rejected") {
      return { icon: ThumbsDown, iconClassName: "border-destructive/30 bg-destructive/10 text-destructive" }
    }
    if (event.status === "offer_more_documents") {
      return { icon: FileWarning, iconClassName: "border-warning/30 bg-warning/10 text-warning" }
    }
    return { icon: ThumbsUp, iconClassName: "border-success/30 bg-success/10 text-success" }
  }
  if (event.direction === "outbound") {
    return { icon: Send, iconClassName: "border-primary/30 bg-primary/10 text-primary" }
  }
  return { icon: Mail, iconClassName: "border-warning/30 bg-warning/10 text-warning" }
}
