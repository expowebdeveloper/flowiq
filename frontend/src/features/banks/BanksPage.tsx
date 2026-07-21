import { useCallback, useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { AlertCircle, Building2, Globe, Loader2, Mail, Plus, Trash2 } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { PageHeader } from "@/components/shared/PageHeader"
import { banksService } from "@/services/banksService"
import type { Bank } from "@/types/api"

export function BanksPage() {
  const navigate = useNavigate()
  const [banks, setBanks] = useState<Bank[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [policyCounts, setPolicyCounts] = useState<Record<number, number>>({})

  const fetchBanks = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    const result = await banksService.listBanks()
    setIsLoading(false)
    if (result.ok && result.data?.banks) {
      setBanks(result.data.banks)
      result.data.banks.forEach((bank) => {
        banksService.listBankPolicies(bank.id).then((res) => {
          if (res.ok && res.data) {
            setPolicyCounts((prev) => ({ ...prev, [bank.id]: res.data!.policies.length }))
          }
        })
      })
    } else {
      setError(result.errorMessage ?? "Failed to load banks.")
    }
  }, [])

  useEffect(() => {
    fetchBanks()
  }, [fetchBanks])

  async function handleDelete(e: React.MouseEvent, bank: Bank) {
    e.stopPropagation()
    if (!confirm(`Delete ${bank.name}? All its loan policies and requirements will also be deleted.`)) return
    const result = await banksService.deleteBank(bank.id)
    if (result.ok) {
      fetchBanks()
    } else {
      alert(result.errorMessage ?? "Error deleting bank")
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <PageHeader title="Banks" description="Manage banks, their supported loan types, and contact details." />
        <Button onClick={() => navigate("/banks/new")} className="gap-2">
          <Plus className="size-4" /> Add Bank
        </Button>
      </div>

      {isLoading && (
        <div className="flex justify-center p-12">
          <Loader2 className="size-8 animate-spin text-primary" />
        </div>
      )}

      {!isLoading && error && (
        <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-4 text-sm text-destructive">
          <AlertCircle className="size-4 shrink-0" /> {error}
        </div>
      )}

      {!isLoading && !error && banks.length === 0 && (
        <div className="rounded-md border border-dashed border-border p-12 text-center text-sm text-muted-foreground">
          <Building2 className="mx-auto mb-3 size-8 text-muted-foreground/60" />
          No banks created yet. Click "Add Bank" to create one.
        </div>
      )}

      {!isLoading && !error && banks.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {banks.map((bank) => (
            <Card
              key={bank.id}
              role="button"
              tabIndex={0}
              onClick={() => navigate(`/banks/${bank.id}`)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") navigate(`/banks/${bank.id}`)
              }}
              className="cursor-pointer transition-colors hover:border-primary/50 hover:bg-accent/30"
            >
              <CardHeader className="flex-row items-start justify-between gap-3 space-y-0">
                <div className="flex min-w-0 items-start gap-3">
                  <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                    {bank.logo ? (
                      <img src={bank.logo} alt={bank.name} className="size-7 object-contain" />
                    ) : (
                      <Building2 className="size-4" />
                    )}
                  </div>
                  <div className="min-w-0">
                    <CardTitle className="truncate">{bank.name}</CardTitle>
                    <Badge variant={bank.status === "active" ? "default" : "secondary"} className="mt-1">
                      {bank.status}
                    </Badge>
                  </div>
                </div>
                <Button
                  variant="outline"
                  size="icon"
                  className="shrink-0 text-destructive hover:bg-destructive/10"
                  onClick={(e) => handleDelete(e, bank)}
                  aria-label="Delete bank"
                >
                  <Trash2 className="size-3.5" />
                </Button>
              </CardHeader>
              <CardContent className="space-y-2 text-xs text-muted-foreground">
                {bank.website && (
                  <div className="flex items-center gap-1.5">
                    <Globe className="size-3 shrink-0" />
                    <span className="truncate">{bank.website}</span>
                  </div>
                )}
                {bank.contact_email && (
                  <div className="flex items-center gap-1.5">
                    <Mail className="size-3 shrink-0" />
                    <span className="truncate">{bank.contact_email}</span>
                  </div>
                )}
                <Badge variant="outline">
                  {policyCounts[bank.id] ?? 0} loan {policyCounts[bank.id] === 1 ? "type" : "types"} configured
                </Badge>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
