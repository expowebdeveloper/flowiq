import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { Loader2 } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { loanApplyService, type LoanApplyResult } from "@/services/loanApplyService"
import { LEAD_STAGE_DEFS, stageOf, type LeadStageKey } from "@/features/leads/leadStage"

function formatBookValue(amount: number): string {
  if (amount >= 1_000_000) return `R${(amount / 1_000_000).toFixed(2)}M`
  if (amount >= 1_000) return `R${(amount / 1_000).toFixed(0)}K`
  return `R${amount.toFixed(0)}`
}

export function PipelineByStage() {
  const [leads, setLeads] = useState<LoanApplyResult[] | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    loanApplyService.list().then((res) => {
      if (cancelled) return
      if (res.ok && res.data) {
        setLeads(res.data)
      } else {
        setErrorMessage(res.errorMessage ?? "Failed to load pipeline")
      }
    })
    return () => {
      cancelled = true
    }
  }, [])

  if (errorMessage) {
    return (
      <Card>
        <CardContent className="p-5 text-sm text-destructive">{errorMessage}</CardContent>
      </Card>
    )
  }

  if (!leads) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 p-5 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" /> Loading pipeline…
        </CardContent>
      </Card>
    )
  }

  const counts = {} as Record<LeadStageKey, number>
  const values = {} as Record<LeadStageKey, number>
  for (const stage of LEAD_STAGE_DEFS) {
    counts[stage.key] = 0
    values[stage.key] = 0
  }

  for (const lead of leads) {
    const stage = stageOf(lead)
    counts[stage] += 1
    values[stage] += lead.loan_amount ?? 0
  }

  const totalBookValue = leads.reduce((sum, lead) => sum + (lead.loan_amount ?? 0), 0)
  const maxCount = Math.max(1, ...LEAD_STAGE_DEFS.map((s) => counts[s.key]))

  return (
    <Card>
      <CardContent className="p-5">
        <div className="mb-4 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            Pipeline by stage
          </h3>
          <span className="text-xs text-muted-foreground">
            Total book value <span className="font-semibold text-foreground">{formatBookValue(totalBookValue)}</span>
          </span>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7">
          {LEAD_STAGE_DEFS.map((stage) => {
            const count = counts[stage.key]
            const barPct = (count / maxCount) * 100
            const isReject = stage.key === "reject"
            return (
              <Link
                key={stage.key}
                to={`/leads?stage=${stage.key}`}
                className={cn(
                  "rounded-lg border p-4 text-left transition-colors",
                  isReject && count > 0
                    ? "border-destructive/30 bg-destructive/5 hover:bg-destructive/10"
                    : "border-border bg-muted/20 hover:bg-accent/50",
                )}
              >
                <div className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  {stage.label}
                </div>
                <div
                  className={cn(
                    "mt-2 text-2xl font-bold",
                    isReject && count > 0 && "text-destructive",
                  )}
                >
                  {count}
                </div>
                <div className="mt-0.5 text-xs text-muted-foreground">{formatBookValue(values[stage.key])}</div>
                <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-border/60">
                  <div
                    className={cn("h-full rounded-full", isReject ? "bg-destructive" : "bg-success")}
                    style={{ width: `${barPct}%` }}
                  />
                </div>
              </Link>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
