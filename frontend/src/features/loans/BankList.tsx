import { useEffect, useState } from "react"
import { AlertCircle, ArrowLeft, Building2, ChevronDown, ExternalLink, Percent } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { banksService } from "@/services/banksService"
import type { BankLoanRate, LoanType } from "@/types/api"
import { LOAN_TYPE_META } from "./loanTypeMeta"

interface BankListProps {
  loanType: LoanType
  onBack: () => void
  onApply: (rate: BankLoanRate) => void
}

export function BankList({ loanType, onBack, onApply }: BankListProps) {
  const [rates, setRates] = useState<BankLoanRate[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setIsLoading(true)
    setError(null)
    banksService.listRates({ loan_type: loanType }).then((res) => {
      if (cancelled) return
      if (res.ok && res.data) {
        setRates(res.data.rates)
      } else {
        setError(res.errorMessage ?? "Failed to load bank rates")
      }
      setIsLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [loanType])

  const meta = LOAN_TYPE_META[loanType]

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={onBack} aria-label="Back to categories">
          <ArrowLeft className="size-4" />
        </Button>
        <div className="flex items-center gap-2">
          <meta.icon className="size-4 text-muted-foreground" />
          <h3 className="text-sm font-medium">{meta.label} — available banks</h3>
        </div>
      </div>

      {isLoading && (
        <div className="grid gap-3 sm:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
      )}

      {!isLoading && error && (
        <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-4 text-sm text-destructive">
          <AlertCircle className="size-4 shrink-0" /> {error}
        </div>
      )}

      {!isLoading && !error && rates && rates.length === 0 && (
        <div className="rounded-md border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
          No banks currently offer {meta.label.toLowerCase()} rates in our database.
        </div>
      )}

      {!isLoading && !error && rates && rates.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2">
          {rates.map((rate) => (
            <BankRateCard key={rate.id} rate={rate} onApply={onApply} />
          ))}
        </div>
      )}
    </div>
  )
}

function BankRateCard({ rate, onApply }: { rate: BankLoanRate; onApply: (rate: BankLoanRate) => void }) {
  const [showAllDocs, setShowAllDocs] = useState(false)
  const hiddenCount = rate.required_documents_list.length - 4
  const visibleDocs = showAllDocs ? rate.required_documents_list : rate.required_documents_list.slice(0, 4)

  return (
    <Card className="flex flex-col">
      <CardHeader className="flex-row items-start gap-3 space-y-0">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-muted">
          <Building2 className="size-4" />
        </div>
        <div className="min-w-0 flex-1">
          <CardTitle>{rate.bank_name}</CardTitle>
          <div className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
            <Percent className="size-3" /> {rate.interest_rate}
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-3">
        {rate.details && <p className="text-xs text-muted-foreground">{rate.details}</p>}

        {rate.required_documents_list.length > 0 && (
          <div>
            <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Required documents
            </p>
            <ul className="space-y-1">
              {visibleDocs.map((doc, i) => (
                <li key={i} className="flex gap-1.5 text-xs text-muted-foreground">
                  <Badge variant="outline" className="h-fit shrink-0 px-1 py-0 text-[10px]">
                    {i + 1}
                  </Badge>
                  <span className="line-clamp-2">{doc}</span>
                </li>
              ))}
            </ul>
            {hiddenCount > 0 && (
              <button
                type="button"
                onClick={() => setShowAllDocs((v) => !v)}
                className="mt-1.5 flex items-center gap-1 text-xs font-medium text-primary hover:underline"
              >
                <ChevronDown className={`size-3 transition-transform ${showAllDocs ? "rotate-180" : ""}`} />
                {showAllDocs ? "Show less" : `+${hiddenCount} more`}
              </button>
            )}
          </div>
        )}

        <div className="mt-auto flex items-center justify-between gap-2 pt-2">
          {rate.source_url ? (
            <a
              href={rate.source_url}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
            >
              <ExternalLink className="size-3" /> Source
            </a>
          ) : (
            <span />
          )}
          <Button size="sm" onClick={() => onApply(rate)}>
            Apply
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
