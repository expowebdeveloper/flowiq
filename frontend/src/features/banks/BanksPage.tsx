import { Fragment, useEffect, useState } from "react"
import {
  Building2,
  Plus,
  Edit2,
  Trash2,
  ChevronDown,
  ChevronUp,
  Globe,
  Loader2,
  AlertCircle,
  Shield,
  FileText,
  Clock,
  Banknote,
  TrendingUp,
  Percent,
  Landmark,
  UserCheck,
  Briefcase,
  Home,
  Sparkles,
  Undo2,
  X,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { banksService } from "@/services/banksService"
import type { Bank, LoanPolicy } from "@/types/api"

const LOAN_TYPES = [
  { value: "home_loan", label: "Home Loan" },
  { value: "education_loan", label: "Education Loan" },
  { value: "personal_loan", label: "Personal Loan" },
  { value: "car_loan", label: "Car Loan" },
  { value: "gold_loan", label: "Gold Loan" },
]

export function BanksPage() {
  const [banks, setBanks] = useState<Bank[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Bank Form State
  const [isBankModalOpen, setIsBankModalOpen] = useState(false)
  const [editingBank, setEditingBank] = useState<Bank | null>(null)
  const [bankForm, setBankForm] = useState({
    name: "",
    website: "",
    logo: "",
    status: "active",
  })
  const [isSavingBank, setIsSavingBank] = useState(false)

  // Expanded Bank ID for Policies
  const [expandedBankId, setExpandedBankId] = useState<number | null>(null)
  const [policies, setPolicies] = useState<Record<number, LoanPolicy[]>>({})
  const [isLoadingPolicies, setIsLoadingPolicies] = useState<Record<number, boolean>>({})

  // View Policy State
  const [viewingPolicy, setViewingPolicy] = useState<LoanPolicy | null>(null)

  // Policy Form State
  const [isPolicyModalOpen, setIsPolicyModalOpen] = useState(false)
  const [editingPolicy, setEditingPolicy] = useState<LoanPolicy | null>(null)
  const [activePolicyBankId, setActivePolicyBankId] = useState<number | null>(null)
  const [isSavingPolicy, setIsSavingPolicy] = useState(false)
  const [policyForm, setPolicyForm] = useState({
    loan_type: "home_loan",
    min_cibil: "700",
    max_cibil: "850",
    min_income: "25000",
    max_loan_amount: "5000000",
    interest_rate: "8.5",
    processing_fee: "0.5",
    max_ltv: "80",
    min_age: "21",
    max_age: "60",
    minimum_work_experience_years: "2",
    maximum_foir: "50",
    employment_types: "Salaried, Self-Employed",
    property_types: "Residential, Commercial",
    required_documents: "PAN Card, Aadhaar Card, 3 Months Salary Slips, 6 Months Bank Statement",
    special_features: "No prepayment penalty",
    prepayment_charges: "0%",
    foreclosure_charges: "0%",
    min_tenure: "12",
    max_tenure: "240",
  })

  // Load Banks
  const fetchBanks = async () => {
    setIsLoading(true)
    setError(null)
    const result = await banksService.listBanks()
    setIsLoading(false)
    if (result.ok && result.data?.banks) {
      setBanks(result.data.banks)
    } else {
      setError(result.errorMessage ?? "Failed to load banks.")
    }
  }

  useEffect(() => {
    fetchBanks()
  }, [])

  // Load Policies for a Bank
  const fetchPolicies = async (bankId: number) => {
    setIsLoadingPolicies((prev) => ({ ...prev, [bankId]: true }))
    const result = await banksService.listBankPolicies(bankId)
    setIsLoadingPolicies((prev) => ({ ...prev, [bankId]: false }))
    if (result.ok && result.data) {
      setPolicies((prev) => ({ ...prev, [bankId]: result.data!.policies }))
    }
  }

  const toggleExpandBank = (bankId: number) => {
    if (expandedBankId === bankId) {
      setExpandedBankId(null)
    } else {
      setExpandedBankId(bankId)
      if (!policies[bankId]) {
        fetchPolicies(bankId)
      }
    }
  }

  // Open modal for Create Bank
  const handleOpenCreateBank = () => {
    setEditingBank(null)
    setBankForm({
      name: "",
      website: "",
      logo: "",
      status: "active",
    })
    setIsBankModalOpen(true)
  }

  // Open modal for Edit Bank
  const handleOpenEditBank = (bank: Bank) => {
    setEditingBank(bank)
    setBankForm({
      name: bank.name,
      website: bank.website ?? "",
      logo: bank.logo ?? "",
      status: bank.status,
    })
    setIsBankModalOpen(true)
  }

  // Save Bank
  const handleSaveBank = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!bankForm.name.trim()) return

    setIsSavingBank(true)
    let result
    if (editingBank) {
      result = await banksService.updateBank(editingBank.id, bankForm)
    } else {
      result = await banksService.createBank(bankForm)
    }
    setIsSavingBank(false)

    if (result.ok) {
      setIsBankModalOpen(false)
      fetchBanks()
    } else {
      alert(result.errorMessage ?? "Error saving bank")
    }
  }

  // Delete Bank
  const handleDeleteBank = async (bankId: number) => {
    if (!confirm("Are you sure you want to delete this bank? All associated policies will also be deleted.")) return
    const result = await banksService.deleteBank(bankId)
    if (result.ok) {
      fetchBanks()
      if (expandedBankId === bankId) {
        setExpandedBankId(null)
      }
    } else {
      alert(result.errorMessage ?? "Error deleting bank")
    }
  }

  // Open modal for Create Policy
  const handleOpenCreatePolicy = (bankId: number) => {
    setActivePolicyBankId(bankId)
    setEditingPolicy(null)
    setPolicyForm({
      loan_type: "home_loan",
      min_cibil: "700",
      max_cibil: "850",
      min_income: "25000",
      max_loan_amount: "5000000",
      interest_rate: "8.5",
      processing_fee: "0.5",
      max_ltv: "80",
      min_age: "21",
      max_age: "60",
      minimum_work_experience_years: "2",
      maximum_foir: "50",
      employment_types: "Salaried, Self-Employed",
      property_types: "Residential, Commercial",
      required_documents: "PAN Card, Aadhaar Card, 3 Months Salary Slips, 6 Months Bank Statement",
      special_features: "No prepayment penalty",
      prepayment_charges: "0%",
      foreclosure_charges: "0%",
      min_tenure: "12",
      max_tenure: "240",
    })
    setIsPolicyModalOpen(true)
  }

  // Open modal for Edit Policy
  const handleOpenEditPolicy = (policy: LoanPolicy) => {
    setEditingPolicy(policy)
    setActivePolicyBankId(policy.bank_id)
    setPolicyForm({
      loan_type: policy.loan_type,
      min_cibil: String(policy.min_cibil),
      max_cibil: String(policy.max_cibil),
      min_income: String(policy.min_income),
      max_loan_amount: String(policy.max_loan_amount),
      interest_rate: String(policy.interest_rate),
      processing_fee: String(policy.processing_fee),
      max_ltv: String(policy.max_ltv),
      min_age: String(policy.min_age),
      max_age: String(policy.max_age),
      minimum_work_experience_years: String(policy.minimum_work_experience_years),
      maximum_foir: String(policy.maximum_foir),
      employment_types: policy.employment_types,
      property_types: policy.property_types,
      required_documents: policy.required_documents,
      special_features: policy.special_features,
      prepayment_charges: policy.prepayment_charges,
      foreclosure_charges: policy.foreclosure_charges,
      min_tenure: String(policy.min_tenure),
      max_tenure: String(policy.max_tenure),
    })
    setIsPolicyModalOpen(true)
  }

  // Save Policy
  const handleSavePolicy = async (e: React.FormEvent) => {
    e.preventDefault()
    if (activePolicyBankId === null) return

    const payload = {
      loan_type: policyForm.loan_type,
      min_cibil: Number(policyForm.min_cibil),
      max_cibil: Number(policyForm.max_cibil),
      min_income: Number(policyForm.min_income),
      max_loan_amount: Number(policyForm.max_loan_amount),
      interest_rate: Number(policyForm.interest_rate),
      processing_fee: Number(policyForm.processing_fee),
      max_ltv: Number(policyForm.max_ltv),
      min_age: Number(policyForm.min_age),
      max_age: Number(policyForm.max_age),
      minimum_work_experience_years: Number(policyForm.minimum_work_experience_years),
      maximum_foir: Number(policyForm.maximum_foir),
      employment_types: policyForm.employment_types,
      property_types: policyForm.property_types,
      required_documents: policyForm.required_documents,
      special_features: policyForm.special_features,
      prepayment_charges: policyForm.prepayment_charges,
      foreclosure_charges: policyForm.foreclosure_charges,
      min_tenure: Number(policyForm.min_tenure),
      max_tenure: Number(policyForm.max_tenure),
    }

    setIsSavingPolicy(true)
    let result
    if (editingPolicy) {
      result = await banksService.updateBankPolicy(editingPolicy.id, payload)
    } else {
      result = await banksService.createBankPolicy(activePolicyBankId, payload)
    }
    setIsSavingPolicy(false)

    if (result.ok) {
      setIsPolicyModalOpen(false)
      fetchPolicies(activePolicyBankId)
    } else {
      alert(result.errorMessage ?? "Error saving policy")
    }
  }

  // Delete Policy
  const handleDeletePolicy = async (policy: LoanPolicy) => {
    if (!confirm("Are you sure you want to delete this policy?")) return
    const result = await banksService.deleteBankPolicy(policy.id)
    if (result.ok) {
      fetchPolicies(policy.bank_id)
    } else {
      alert(result.errorMessage ?? "Error deleting policy")
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Banks & Policies</h2>
          <p className="text-sm text-muted-foreground">
            Manage banks, sync settings, and configure credit policy parameters.
          </p>
        </div>
        <Button onClick={handleOpenCreateBank} className="gap-2">
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
        <Card className="overflow-hidden">
          <div className="w-full overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="px-4 py-3 font-medium sm:px-6">Bank Name</th>
                  <th className="px-4 py-3 font-medium sm:px-6">Website</th>
                  <th className="px-4 py-3 font-medium sm:px-6">Status</th>
                  <th className="px-4 py-3 text-right font-medium sm:px-6">Actions</th>
                </tr>
              </thead>
              <tbody>
                {banks.map((bank) => {
                  const isExpanded = expandedBankId === bank.id
                  const bankPolicies = policies[bank.id] ?? []
                  const isPoliciesLoading = isLoadingPolicies[bank.id]

                  return (
                    <Fragment key={bank.id}>
                      <tr className="border-b border-border transition-colors last:border-b-0 hover:bg-muted/20">
                        <td className="px-4 py-3 sm:px-6">
                          <div className="flex items-center gap-3">
                            <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                              {bank.logo ? (
                                <img src={bank.logo} alt={bank.name} className="size-7 object-contain" />
                              ) : (
                                <Building2 className="size-4" />
                              )}
                            </div>
                            <span className="font-medium">{bank.name}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 sm:px-6">
                          {bank.website ? (
                            <a
                              href={bank.website}
                              target="_blank"
                              rel="noreferrer"
                              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                            >
                              <Globe className="size-3" /> {bank.website}
                            </a>
                          ) : (
                            <span className="text-xs text-muted-foreground">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 sm:px-6">
                          <Badge variant={bank.status === "active" ? "default" : "secondary"}>
                            {bank.status}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 sm:px-6">
                          <div className="flex items-center justify-end gap-2">
                            <Button variant="outline" size="sm" onClick={() => handleOpenEditBank(bank)}>
                              <Edit2 className="size-3.5" />
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleDeleteBank(bank.id)}
                              className="text-destructive hover:bg-destructive/10"
                            >
                              <Trash2 className="size-3.5" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => toggleExpandBank(bank.id)} className="gap-1.5">
                              {isExpanded ? (
                                <>
                                  Hide Policies <ChevronUp className="size-4" />
                                </>
                              ) : (
                                <>
                                  Show Policies <ChevronDown className="size-4" />
                                </>
                              )}
                            </Button>
                          </div>
                        </td>
                      </tr>

                      {isExpanded && (
                        <tr key={`${bank.id}-policies`} className="border-b border-border last:border-b-0">
                          <td colSpan={4} className="bg-muted/20 p-4 sm:p-6">
                            <div className="flex items-center justify-between mb-4">
                              <h4 className="text-sm font-medium">Loan Policies</h4>
                              <Button size="sm" variant="outline" onClick={() => handleOpenCreatePolicy(bank.id)} className="gap-1">
                                <Plus className="size-3.5" /> Add Policy
                              </Button>
                            </div>

                            {isPoliciesLoading ? (
                              <div className="flex justify-center p-6">
                                <Loader2 className="size-6 animate-spin text-primary" />
                              </div>
                            ) : bankPolicies.length === 0 ? (
                              <div className="text-center p-6 text-xs text-muted-foreground border border-dashed rounded-md">
                                No policies configured for this bank yet.
                              </div>
                            ) : (
                              <div className="grid gap-3 sm:grid-cols-2">
                                {bankPolicies.map((policy) => (
                                  <Card
                                    key={policy.id}
                                    role="button"
                                    tabIndex={0}
                                    onClick={() => setViewingPolicy(policy)}
                                    onKeyDown={(e) => {
                                      if (e.key === "Enter" || e.key === " ") {
                                        e.preventDefault()
                                        setViewingPolicy(policy)
                                      }
                                    }}
                                    className="relative overflow-hidden bg-background cursor-pointer transition-colors hover:border-primary/50 hover:bg-accent/30"
                                  >
                                    <CardHeader className="p-3 pb-2 flex-row justify-between items-start space-y-0">
                                      <div>
                                        <Badge className="capitalize">
                                          {policy.loan_type.replace("_", " ")}
                                        </Badge>
                                        <div className="mt-1 text-sm font-semibold text-primary">
                                          {policy.interest_rate}% p.a.
                                        </div>
                                      </div>
                                      <div className="flex gap-1">
                                        <Button
                                          size="icon"
                                          variant="ghost"
                                          className="size-7"
                                          onClick={(e) => {
                                            e.stopPropagation()
                                            handleOpenEditPolicy(policy)
                                          }}
                                        >
                                          <Edit2 className="size-3" />
                                        </Button>
                                        <Button
                                          size="icon"
                                          variant="ghost"
                                          className="size-7 text-destructive"
                                          onClick={(e) => {
                                            e.stopPropagation()
                                            handleDeletePolicy(policy)
                                          }}
                                        >
                                          <Trash2 className="size-3" />
                                        </Button>
                                      </div>
                                    </CardHeader>

                                    <CardContent className="p-3 pt-0 text-xs space-y-2">
                                      <div className="grid grid-cols-2 gap-x-2 gap-y-1.5 text-muted-foreground border-t pt-2">
                                        <div className="flex items-center gap-1">
                                          <Shield className="size-3 text-muted-foreground/70" />
                                          <span>CIBIL: {policy.min_cibil} - {policy.max_cibil}</span>
                                        </div>
                                        <div className="flex items-center gap-1">
                                          <Clock className="size-3 text-muted-foreground/70" />
                                          <span>Tenure: {policy.min_tenure}-{policy.max_tenure}m</span>
                                        </div>
                                        <div className="flex items-center gap-1 col-span-2">
                                          <FileText className="size-3 text-muted-foreground/70" />
                                          <span className="truncate">Docs: {policy.required_documents}</span>
                                        </div>
                                      </div>
                                    </CardContent>
                                  </Card>
                                ))}
                              </div>
                            )}
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Bank Modal */}
      {isBankModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in">
          <div className="w-full max-w-md rounded-lg border border-border bg-background p-6 shadow-lg animate-in zoom-in-95">
            <h3 className="text-lg font-semibold">{editingBank ? "Edit Bank" : "Add Bank"}</h3>
            <form onSubmit={handleSaveBank} className="mt-4 space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="bank-name">Bank Name</Label>
                <Input
                  id="bank-name"
                  value={bankForm.name}
                  onChange={(e) => setBankForm((prev) => ({ ...prev, name: e.target.value }))}
                  placeholder="e.g. State Bank of India"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="bank-website">Website URL (optional)</Label>
                <Input
                  id="bank-website"
                  type="url"
                  value={bankForm.website}
                  onChange={(e) => setBankForm((prev) => ({ ...prev, website: e.target.value }))}
                  placeholder="https://..."
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="bank-logo">Logo Image URL (optional)</Label>
                <Input
                  id="bank-logo"
                  value={bankForm.logo}
                  onChange={(e) => setBankForm((prev) => ({ ...prev, logo: e.target.value }))}
                  placeholder="https://.../logo.png"
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="bank-status">Status</Label>
                <Select
                  value={bankForm.status}
                  onValueChange={(val) => setBankForm((prev) => ({ ...prev, status: val }))}
                >
                  <SelectTrigger id="bank-status">
                    <SelectValue placeholder="Select status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="inactive">Inactive</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setIsBankModalOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isSavingBank}>
                  {isSavingBank ? <Loader2 className="size-4 animate-spin" /> : "Save"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* View Policy Modal */}
      {viewingPolicy && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in">
          <div className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-lg border border-border bg-background shadow-lg animate-in zoom-in-95">
            <div className="flex shrink-0 items-start justify-between gap-4 border-b border-border p-6 pb-4">
              <div>
                <Badge className="capitalize">{viewingPolicy.loan_type.replace("_", " ")}</Badge>
                <h3 className="mt-2 text-lg font-semibold">Loan Policy Details</h3>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5"
                  onClick={() => {
                    const policy = viewingPolicy
                    setViewingPolicy(null)
                    handleOpenEditPolicy(policy)
                  }}
                >
                  <Edit2 className="size-3.5" /> Edit
                </Button>
                <Button size="icon" variant="ghost" onClick={() => setViewingPolicy(null)}>
                  <X className="size-4" />
                </Button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              <div className="grid gap-4 sm:grid-cols-2">
                <PolicyDetailRow icon={Percent} label="Interest rate" value={`${viewingPolicy.interest_rate}% p.a.`} />
                <PolicyDetailRow icon={Banknote} label="Processing fee" value={`${viewingPolicy.processing_fee}%`} />
                <PolicyDetailRow icon={Shield} label="CIBIL score range" value={`${viewingPolicy.min_cibil} - ${viewingPolicy.max_cibil}`} />
                <PolicyDetailRow icon={Clock} label="Tenure" value={`${viewingPolicy.min_tenure} - ${viewingPolicy.max_tenure} months`} />
                <PolicyDetailRow icon={TrendingUp} label="Min monthly income" value={formatCurrencyValue(viewingPolicy.min_income)} />
                <PolicyDetailRow icon={Landmark} label="Max loan amount" value={formatCurrencyValue(viewingPolicy.max_loan_amount)} />
                <PolicyDetailRow icon={Percent} label="Max LTV" value={`${viewingPolicy.max_ltv}%`} />
                <PolicyDetailRow icon={UserCheck} label="Age eligibility" value={`${viewingPolicy.min_age} - ${viewingPolicy.max_age} years`} />
                <PolicyDetailRow icon={Briefcase} label="Min work experience" value={`${viewingPolicy.minimum_work_experience_years} years`} />
                <PolicyDetailRow icon={Percent} label="Maximum FOIR" value={`${viewingPolicy.maximum_foir}%`} />
                <PolicyDetailRow icon={Briefcase} label="Employment types" value={viewingPolicy.employment_types} />
                <PolicyDetailRow icon={Home} label="Property types" value={viewingPolicy.property_types} />
                <PolicyDetailRow icon={Undo2} label="Prepayment charges" value={viewingPolicy.prepayment_charges} />
                <PolicyDetailRow icon={Undo2} label="Foreclosure charges" value={viewingPolicy.foreclosure_charges} />
                <PolicyDetailRow icon={FileText} label="Required documents" value={viewingPolicy.required_documents} fullWidth />
                {viewingPolicy.special_features && (
                  <PolicyDetailRow icon={Sparkles} label="Special features" value={viewingPolicy.special_features} fullWidth />
                )}
                {viewingPolicy.last_updated && (
                  <PolicyDetailRow icon={Clock} label="Last updated" value={formatDateTime(viewingPolicy.last_updated)} fullWidth />
                )}
              </div>
            </div>

            <div className="flex shrink-0 justify-end gap-2 border-t border-border p-4">
              <Button variant="outline" onClick={() => setViewingPolicy(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Policy Modal */}
      {isPolicyModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in">
          <div className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-lg border border-border bg-background shadow-lg animate-in zoom-in-95">
            <h3 className="shrink-0 border-b border-border p-6 pb-4 text-lg font-semibold">
              {editingPolicy ? "Edit Loan Policy" : "Add Loan Policy"}
            </h3>
            <form
              onSubmit={handleSavePolicy}
              className="grid flex-1 auto-rows-min gap-4 overflow-y-auto p-6 sm:grid-cols-2"
            >
              <div className="space-y-1.5">
                <Label>Loan Type</Label>
                <Select
                  value={policyForm.loan_type}
                  onValueChange={(val) => setPolicyForm((prev) => ({ ...prev, loan_type: val }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    {LOAN_TYPES.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        {type.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <Label>Interest Rate (% p.a.)</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={policyForm.interest_rate}
                  onChange={(e) => setPolicyForm((prev) => ({ ...prev, interest_rate: e.target.value }))}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label>Min CIBIL Score</Label>
                <Input
                  type="number"
                  value={policyForm.min_cibil}
                  onChange={(e) => setPolicyForm((prev) => ({ ...prev, min_cibil: e.target.value }))}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label>Max CIBIL Score</Label>
                <Input
                  type="number"
                  value={policyForm.max_cibil}
                  onChange={(e) => setPolicyForm((prev) => ({ ...prev, max_cibil: e.target.value }))}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label>Min Monthly Income (₹)</Label>
                <Input
                  type="number"
                  value={policyForm.min_income}
                  onChange={(e) => setPolicyForm((prev) => ({ ...prev, min_income: e.target.value }))}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label>Max Loan Amount (₹)</Label>
                <Input
                  type="number"
                  value={policyForm.max_loan_amount}
                  onChange={(e) => setPolicyForm((prev) => ({ ...prev, max_loan_amount: e.target.value }))}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label>Processing Fee (%)</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={policyForm.processing_fee}
                  onChange={(e) => setPolicyForm((prev) => ({ ...prev, processing_fee: e.target.value }))}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label>Max LTV (%)</Label>
                <Input
                  type="number"
                  step="0.1"
                  value={policyForm.max_ltv}
                  onChange={(e) => setPolicyForm((prev) => ({ ...prev, max_ltv: e.target.value }))}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label>Min Age</Label>
                <Input
                  type="number"
                  value={policyForm.min_age}
                  onChange={(e) => setPolicyForm((prev) => ({ ...prev, min_age: e.target.value }))}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label>Max Age</Label>
                <Input
                  type="number"
                  value={policyForm.max_age}
                  onChange={(e) => setPolicyForm((prev) => ({ ...prev, max_age: e.target.value }))}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label>Min Work Experience (Years)</Label>
                <Input
                  type="number"
                  value={policyForm.minimum_work_experience_years}
                  onChange={(e) => setPolicyForm((prev) => ({ ...prev, minimum_work_experience_years: e.target.value }))}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label>Maximum FOIR (%)</Label>
                <Input
                  type="number"
                  value={policyForm.maximum_foir}
                  onChange={(e) => setPolicyForm((prev) => ({ ...prev, maximum_foir: e.target.value }))}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label>Min Tenure (Months)</Label>
                <Input
                  type="number"
                  value={policyForm.min_tenure}
                  onChange={(e) => setPolicyForm((prev) => ({ ...prev, min_tenure: e.target.value }))}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label>Max Tenure (Months)</Label>
                <Input
                  type="number"
                  value={policyForm.max_tenure}
                  onChange={(e) => setPolicyForm((prev) => ({ ...prev, max_tenure: e.target.value }))}
                  required
                />
              </div>

              <div className="space-y-1.5 sm:col-span-2">
                <Label>Employment Types</Label>
                <Input
                  value={policyForm.employment_types}
                  onChange={(e) => setPolicyForm((prev) => ({ ...prev, employment_types: e.target.value }))}
                  placeholder="e.g. Salaried, Self-Employed"
                  required
                />
              </div>

              <div className="space-y-1.5 sm:col-span-2">
                <Label>Property Types</Label>
                <Input
                  value={policyForm.property_types}
                  onChange={(e) => setPolicyForm((prev) => ({ ...prev, property_types: e.target.value }))}
                  placeholder="e.g. Residential, Commercial"
                  required
                />
              </div>

              <div className="space-y-1.5 sm:col-span-2">
                <Label>Required Documents (comma separated)</Label>
                <Input
                  value={policyForm.required_documents}
                  onChange={(e) => setPolicyForm((prev) => ({ ...prev, required_documents: e.target.value }))}
                  placeholder="PAN Card, Aadhaar Card"
                  required
                />
              </div>

              <div className="space-y-1.5 sm:col-span-2">
                <Label>Special Features (optional)</Label>
                <Textarea
                  value={policyForm.special_features}
                  onChange={(e) => setPolicyForm((prev) => ({ ...prev, special_features: e.target.value }))}
                  placeholder="e.g. Balance transfer option available"
                />
              </div>

              <div className="space-y-1.5">
                <Label>Prepayment Charges</Label>
                <Input
                  value={policyForm.prepayment_charges}
                  onChange={(e) => setPolicyForm((prev) => ({ ...prev, prepayment_charges: e.target.value }))}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label>Foreclosure Charges</Label>
                <Input
                  value={policyForm.foreclosure_charges}
                  onChange={(e) => setPolicyForm((prev) => ({ ...prev, foreclosure_charges: e.target.value }))}
                  required
                />
              </div>

              <div className="flex justify-end gap-2 sm:col-span-2">
                <Button type="button" variant="outline" onClick={() => setIsPolicyModalOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isSavingPolicy}>
                  {isSavingPolicy ? <Loader2 className="size-4 animate-spin" /> : "Save"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

function formatCurrencyValue(amount: number): string {
  return `₹${new Intl.NumberFormat("en-IN").format(amount)}`
}

function formatDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })
  } catch {
    return iso
  }
}

function PolicyDetailRow({
  icon: Icon,
  label,
  value,
  fullWidth,
}: {
  icon: typeof Shield
  label: string
  value: string
  fullWidth?: boolean
}) {
  return (
    <div className={fullWidth ? "sm:col-span-2" : undefined}>
      <div className="flex items-start gap-3">
        <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
        <div className="min-w-0">
          <div className="text-xs text-muted-foreground">{label}</div>
          <div className="text-sm font-medium">{value}</div>
        </div>
      </div>
    </div>
  )
}
