import { useCallback, useEffect, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import {
  AlertCircle,
  ArrowLeft,
  Building2,
  ChevronDown,
  ClipboardList,
  Edit2,
  Eye,
  EyeOff,
  Globe,
  Loader2,
  Lock,
  Mail,
  Paperclip,
  User,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Switch } from "@/components/ui/switch"
import { banksService, type BankPayload } from "@/services/banksService"
import type { Bank, LoanPolicy, LoanRequirement } from "@/types/api"
import { LOAN_TYPE_META, LOAN_TYPES, loanTypeLabel } from "@/features/loans/loanTypeMeta"
import { BankForm } from "./BankForm"
import { RequirementBoard } from "@/features/loan-requirements/RequirementBoard"

type ScopedRequirement = LoanRequirement & { scope: "Global" | "Bank" }

const PREVIEW_LIMIT = 3

function normalizeRequirements(commands: LoanRequirement[] | undefined): LoanRequirement[] {
  return Array.isArray(commands)
    ? commands.map((requirement) => ({
        ...requirement,
        loan_types: Array.isArray(requirement.loan_types) ? requirement.loan_types : [],
      }))
    : []
}

function toBankPayload(bank: Bank): BankPayload {
  return {
    name: bank.name,
    website: bank.website ?? "",
    logo: bank.logo ?? "",
    status: bank.status,
    contact_email: bank.contact_email ?? "",
    portal_url: bank.portal_url ?? "",
    portal_username: bank.portal_username ?? "",
    portal_password: bank.portal_password ?? "",
  }
}

export function BankDetailPage() {
  const { bankId: bankIdParam } = useParams<{ bankId: string }>()
  const bankId = Number(bankIdParam)
  const navigate = useNavigate()

  const [bank, setBank] = useState<Bank | null>(null)
  const [isLoadingBank, setIsLoadingBank] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [isEditingBank, setIsEditingBank] = useState(false)
  const [bankForm, setBankForm] = useState<BankPayload | null>(null)
  const [isSavingBank, setIsSavingBank] = useState(false)
  const [showPortalPassword, setShowPortalPassword] = useState(false)

  const [policies, setPolicies] = useState<LoanPolicy[]>([])
  const [isLoadingPolicies, setIsLoadingPolicies] = useState(true)
  const [togglingLoanType, setTogglingLoanType] = useState<string | null>(null)
  const [expandedPreviewType, setExpandedPreviewType] = useState<string | null>(null)
  const [previewRequirement, setPreviewRequirement] = useState<ScopedRequirement | null>(null)

  const [requirements, setRequirements] = useState<LoanRequirement[] | null>(null)
  const [isLoadingRequirements, setIsLoadingRequirements] = useState(true)
  const [requirementsError, setRequirementsError] = useState<string | null>(null)

  // Fetched only for the "Supported Loan Types" preview below — it needs to
  // show the FULL effective set of requirements for a loan type (global +
  // bank-specific), while the "Additional Requirements" section itself only
  // manages this bank's own ones (global ones are managed on the Loan Type
  // Configuration page).
  const [globalRequirements, setGlobalRequirements] = useState<LoanRequirement[]>([])

  const fetchBank = useCallback(async () => {
    setIsLoadingBank(true)
    setError(null)
    const result = await banksService.listBanks()
    setIsLoadingBank(false)
    if (result.ok && result.data?.banks) {
      const found = result.data.banks.find((b) => b.id === bankId)
      if (found) {
        setBank(found)
      } else {
        setError("Bank not found.")
      }
    } else {
      setError(result.errorMessage ?? "Failed to load bank.")
    }
  }, [bankId])

  const fetchPolicies = useCallback(async () => {
    setIsLoadingPolicies(true)
    const result = await banksService.listBankPolicies(bankId)
    setIsLoadingPolicies(false)
    if (result.ok && result.data) {
      setPolicies(Array.isArray(result.data.policies) ? result.data.policies : [])
    } else {
      setPolicies([])
    }
  }, [bankId])

  const fetchRequirements = useCallback(() => {
    setIsLoadingRequirements(true)
    setRequirementsError(null)
    banksService.listBankRequirements(bankId).then((result) => {
      setIsLoadingRequirements(false)
      if (result.ok && result.data) {
        setRequirements(normalizeRequirements(result.data.commands))
      } else {
        setRequirements([])
        setRequirementsError(result.errorMessage ?? "Failed to load requirements")
      }
    })
  }, [bankId])

  const fetchGlobalRequirements = useCallback(() => {
    banksService.listGlobalRequirements().then((result) => {
      if (result.ok && result.data) {
        setGlobalRequirements(normalizeRequirements(result.data.commands))
      } else {
        setGlobalRequirements([])
      }
    })
  }, [])

  useEffect(() => {
    fetchBank()
    fetchPolicies()
    fetchRequirements()
    fetchGlobalRequirements()
  }, [fetchBank, fetchPolicies, fetchRequirements, fetchGlobalRequirements])

  function startEditingBank() {
    if (!bank) return
    setBankForm(toBankPayload(bank))
    setShowPortalPassword(false)
    setIsEditingBank(true)
  }

  async function handleSaveBank(e: React.FormEvent) {
    e.preventDefault()
    if (!bank || !bankForm || !bankForm.name.trim()) return

    setIsSavingBank(true)
    const result = await banksService.updateBank(bank.id, bankForm)
    setIsSavingBank(false)

    if (result.ok) {
      setIsEditingBank(false)
      fetchBank()
    } else {
      alert(result.errorMessage ?? "Error saving bank")
    }
  }

  async function handleToggleLoanType(loanType: string, existing: LoanPolicy | undefined, checked: boolean) {
    setTogglingLoanType(loanType)
    if (checked) {
      const result = await banksService.createBankPolicy(bankId, { loan_type: loanType })
      if (!result.ok) alert(result.errorMessage ?? "Error enabling loan type")
    } else if (existing) {
      if (!confirm(`Stop offering ${LOAN_TYPE_META[loanType as keyof typeof LOAN_TYPE_META].label} at this bank?`)) {
        setTogglingLoanType(null)
        return
      }
      const result = await banksService.deleteBankPolicy(existing.id)
      if (!result.ok) alert(result.errorMessage ?? "Error disabling loan type")
    }
    await fetchPolicies()
    setTogglingLoanType(null)
  }

  if (isLoadingBank) {
    return (
      <div className="flex justify-center p-12">
        <Loader2 className="size-8 animate-spin text-primary" />
      </div>
    )
  }

  if (error || !bank) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/banks")} aria-label="Back to banks">
          <ArrowLeft className="size-4" />
        </Button>
        <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-4 text-sm text-destructive">
          <AlertCircle className="size-4 shrink-0" /> {error ?? "Bank not found."}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => navigate("/banks")} aria-label="Back to banks">
          <ArrowLeft className="size-4" />
        </Button>
        <h2 className="text-sm font-medium text-muted-foreground">Banks — {bank.name}</h2>
      </div>

      <Card>
        {isEditingBank && bankForm ? (
          <CardContent className="space-y-6 pt-6">
            <form onSubmit={handleSaveBank} className="space-y-6">
              <BankForm value={bankForm} onChange={setBankForm} />
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setIsEditingBank(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isSavingBank}>
                  {isSavingBank && <Loader2 className="size-4 animate-spin" />}
                  Save
                </Button>
              </div>
            </form>
          </CardContent>
        ) : (
          <CardHeader className="flex-row items-start justify-between gap-3 space-y-0">
            <div className="flex min-w-0 items-start gap-3">
              <div className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                {bank.logo ? (
                  <img src={bank.logo} alt={bank.name} className="size-8 object-contain" />
                ) : (
                  <Building2 className="size-5" />
                )}
              </div>
              <div className="min-w-0 space-y-2">
                <div>
                  <CardTitle className="text-xl">{bank.name}</CardTitle>
                  <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
                    <Badge variant={bank.status === "active" ? "default" : "secondary"}>{bank.status}</Badge>
                    {bank.website && (
                      <a
                        href={bank.website}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-1 hover:text-foreground"
                      >
                        <Globe className="size-3" /> {bank.website}
                      </a>
                    )}
                    {bank.contact_email && (
                      <span className="flex items-center gap-1">
                        <Mail className="size-3" /> {bank.contact_email}
                      </span>
                    )}
                  </div>
                </div>

                {(bank.portal_url || bank.portal_username || bank.portal_password) && (
                  <div className="rounded-md border border-dashed border-border p-3">
                    <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Bank Portal Login
                    </p>
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
                      {bank.portal_url && (
                        <a
                          href={bank.portal_url}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center gap-1 hover:text-foreground"
                        >
                          <Globe className="size-3" /> {bank.portal_url}
                        </a>
                      )}
                      {bank.portal_username && (
                        <span className="flex items-center gap-1">
                          <User className="size-3" /> {bank.portal_username}
                        </span>
                      )}
                      {bank.portal_password && (
                        <span className="flex items-center gap-1">
                          <Lock className="size-3" />
                          {showPortalPassword ? bank.portal_password : "••••••••"}
                          <button
                            type="button"
                            onClick={() => setShowPortalPassword((v) => !v)}
                            className="text-muted-foreground hover:text-foreground"
                            aria-label={showPortalPassword ? "Hide portal password" : "Show portal password"}
                          >
                            {showPortalPassword ? <EyeOff className="size-3" /> : <Eye className="size-3" />}
                          </button>
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
            <Button variant="outline" size="sm" className="shrink-0 gap-1.5" onClick={startEditingBank}>
              <Edit2 className="size-3.5" /> Edit Bank
            </Button>
          </CardHeader>
        )}
      </Card>

      <div className="space-y-3">
        <div>
          <h3 className="text-sm font-medium">Supported Loan Types</h3>
          <p className="text-xs text-muted-foreground">
            Turn on the loan types this bank offers. Each card previews its requirements from below —
            manage them in "Additional Requirements" underneath.
          </p>
        </div>

        {isLoadingPolicies ? (
          <div className="flex justify-center p-8">
            <Loader2 className="size-6 animate-spin text-primary" />
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {LOAN_TYPES.map((loanType) => {
              const meta = LOAN_TYPE_META[loanType]
              const existing = policies.find((p) => p.loan_type === loanType)
              const isSupported = Boolean(existing)
              const matchesType = (r: LoanRequirement) => {
                const loanTypes = Array.isArray(r.loan_types) ? r.loan_types : []
                return loanTypes.length === 0 || loanTypes.includes(loanType)
              }
              const matchingRequirements: ScopedRequirement[] = [
                ...globalRequirements.filter(matchesType).map((r) => ({ ...r, scope: "Global" as const })),
                ...(requirements ?? []).filter(matchesType).map((r) => ({ ...r, scope: "Bank" as const })),
              ]
              const isExpanded = expandedPreviewType === loanType
              const visibleRequirements = isExpanded ? matchingRequirements : matchingRequirements.slice(0, PREVIEW_LIMIT)
              const hiddenCount = matchingRequirements.length - visibleRequirements.length

              return (
                <Card key={loanType} className={isSupported ? "border-primary/40" : undefined}>
                  <CardHeader className="flex-row items-center justify-between gap-3 space-y-0 pb-2">
                    <div className="flex items-center gap-2">
                      <meta.icon className="size-4 text-muted-foreground" />
                      <CardTitle className="text-sm">{meta.label}</CardTitle>
                    </div>
                    <Switch
                      checked={isSupported}
                      disabled={togglingLoanType === loanType}
                      onCheckedChange={(checked) => handleToggleLoanType(loanType, existing, checked)}
                      aria-label={`Toggle ${meta.label} support`}
                    />
                  </CardHeader>
                  {isSupported && (
                    <CardContent className="space-y-1 pt-0">
                      {matchingRequirements.length === 0 ? (
                        <p className="text-xs italic text-muted-foreground">No requirements set yet.</p>
                      ) : (
                        <>
                          <div className="space-y-1">
                            {visibleRequirements.map((req) => (
                              <button
                                key={`${req.scope}-${req.id}`}
                                type="button"
                                onClick={() => setPreviewRequirement(req)}
                                className="flex w-full items-center gap-2 rounded-md border border-transparent px-1.5 py-1 text-left text-xs transition-colors hover:border-border hover:bg-accent/50"
                              >
                                <ClipboardList className="size-3 shrink-0 text-muted-foreground" />
                                <span className="min-w-0 flex-1 truncate">{req.scenario}</span>
                                <Badge
                                  variant={req.scope === "Global" ? "secondary" : "outline"}
                                  className="h-fit shrink-0 px-1.5 py-0 text-[9px]"
                                >
                                  {req.scope}
                                </Badge>
                                {req.attachment_url && <Paperclip className="size-3 shrink-0 text-muted-foreground" />}
                              </button>
                            ))}
                          </div>
                          {hiddenCount > 0 && (
                            <button
                              type="button"
                              onClick={() => setExpandedPreviewType(loanType)}
                              className="flex items-center gap-1 px-1.5 text-xs font-medium text-primary hover:underline"
                            >
                              <ChevronDown className="size-3" /> +{hiddenCount} more
                            </button>
                          )}
                          {isExpanded && matchingRequirements.length > PREVIEW_LIMIT && (
                            <button
                              type="button"
                              onClick={() => setExpandedPreviewType(null)}
                              className="flex items-center gap-1 px-1.5 text-xs font-medium text-primary hover:underline"
                            >
                              <ChevronDown className="size-3 rotate-180" /> Show less
                            </button>
                          )}
                        </>
                      )}
                    </CardContent>
                  )}
                </Card>
              )
            })}
          </div>
        )}
      </div>

      <div className="space-y-3">
        <div>
          <h3 className="text-sm font-medium">Additional Requirements for {bank.name}</h3>
          <p className="text-xs text-muted-foreground">
            Bank-specific instructions for the loan-processing agent, on top of the global Loan Requirements
            list.
          </p>
        </div>
        <RequirementBoard
          requirements={requirements}
          isLoading={isLoadingRequirements}
          error={requirementsError}
          addButtonLabel="Add Requirement"
          emptyStateText={`No requirements set for ${bank.name} yet.`}
          onCreate={(payload) => banksService.createBankRequirement(bankId, payload)}
          onUpdate={(id, payload) => banksService.updateRequirement(id, payload)}
          onDelete={(id) => banksService.deleteRequirement(id)}
          onChanged={fetchRequirements}
        />
      </div>

      <Dialog open={previewRequirement !== null} onOpenChange={(open) => !open && setPreviewRequirement(null)}>
        <DialogContent className="max-w-lg">
          {previewRequirement && (
            <>
              <DialogHeader>
                <div className="flex items-center gap-2">
                  <DialogTitle>{previewRequirement.scenario}</DialogTitle>
                  <Badge variant={previewRequirement.scope === "Global" ? "secondary" : "outline"}>
                    {previewRequirement.scope}
                  </Badge>
                </div>
              </DialogHeader>
              <div className="space-y-3">
                <div className="flex flex-wrap gap-1">
                  {previewRequirement.loan_types.length === 0 ? (
                    <Badge variant="outline">All loan types</Badge>
                  ) : (
                    previewRequirement.loan_types.map((type) => (
                      <Badge key={type} variant="outline">
                        {loanTypeLabel(type)}
                      </Badge>
                    ))
                  )}
                </div>
                <p className="text-sm text-muted-foreground">{previewRequirement.instruction}</p>
                {previewRequirement.attachment_url && (
                  <a
                    href={previewRequirement.attachment_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1.5 text-xs text-primary hover:underline"
                  >
                    <Paperclip className="size-3" /> {previewRequirement.attachment_filename}
                  </a>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
