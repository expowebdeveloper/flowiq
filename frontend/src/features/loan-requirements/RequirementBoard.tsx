import { useState } from "react"
import {
  AlertCircle,
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  ClipboardList,
  Edit2,
  Layers,
  Loader2,
  Paperclip,
  Plus,
  Trash2,
  X,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Textarea } from "@/components/ui/textarea"
import type { LoanRequirementPayload } from "@/services/banksService"
import type { LoanRequirement } from "@/types/api"
import { LOAN_TYPE_META, LOAN_TYPES } from "@/features/loans/loanTypeMeta"

const ALL_LOAN_TYPES_KEY = "__all__"

const GROUPS = [
  { key: ALL_LOAN_TYPES_KEY, label: "All Loan Types", icon: Layers },
  ...LOAN_TYPES.map((type) => ({ key: type, label: LOAN_TYPE_META[type].label, icon: LOAN_TYPE_META[type].icon })),
]

interface RequirementBoardProps {
  requirements: LoanRequirement[] | null
  isLoading: boolean
  error: string | null
  addButtonLabel: string
  emptyStateText: string
  onCreate: (payload: LoanRequirementPayload) => Promise<{ ok: boolean; errorMessage?: string }>
  onUpdate: (id: number, payload: LoanRequirementPayload) => Promise<{ ok: boolean; errorMessage?: string }>
  onDelete: (id: number) => Promise<{ ok: boolean; errorMessage?: string }>
  onChanged: () => void
}

const emptyForm = {
  scenario: "",
  instruction: "",
  applyToAll: true,
  selectedTypes: [] as string[],
  attachmentFile: null as File | null,
  removeAttachment: false,
  existingAttachmentFilename: null as string | null,
}

export function RequirementBoard({
  requirements,
  isLoading,
  error,
  addButtonLabel,
  emptyStateText,
  onCreate,
  onUpdate,
  onDelete,
  onChanged,
}: RequirementBoardProps) {
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null)

  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState(emptyForm)
  const [isSaving, setIsSaving] = useState(false)
  const [fileInputKey, setFileInputKey] = useState(0)

  function openCreate(defaultGroup: string) {
    setEditingId(null)
    setForm(
      defaultGroup === ALL_LOAN_TYPES_KEY
        ? emptyForm
        : { ...emptyForm, applyToAll: false, selectedTypes: [defaultGroup] },
    )
    setFileInputKey((k) => k + 1)
    setIsModalOpen(true)
  }

  function openEdit(requirement: LoanRequirement) {
    setEditingId(requirement.id)
    setForm({
      scenario: requirement.scenario,
      instruction: requirement.instruction,
      applyToAll: requirement.loan_types.length === 0,
      selectedTypes: requirement.loan_types,
      attachmentFile: null,
      removeAttachment: false,
      existingAttachmentFilename: requirement.attachment_filename,
    })
    setFileInputKey((k) => k + 1)
    setIsModalOpen(true)
  }

  function toggleAll(checked: boolean) {
    setForm((prev) => ({ ...prev, applyToAll: checked, selectedTypes: checked ? [] : prev.selectedTypes }))
  }

  function toggleType(type: string, checked: boolean) {
    setForm((prev) => ({
      ...prev,
      applyToAll: false,
      selectedTypes: checked ? [...prev.selectedTypes, type] : prev.selectedTypes.filter((t) => t !== type),
    }))
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null
    setForm((prev) => ({ ...prev, attachmentFile: file, removeAttachment: false }))
  }

  function handleRemoveAttachment() {
    setForm((prev) => ({ ...prev, attachmentFile: null, removeAttachment: true, existingAttachmentFilename: null }))
    setFileInputKey((k) => k + 1)
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    if (!form.scenario.trim() || !form.instruction.trim()) return
    if (!form.applyToAll && form.selectedTypes.length === 0) {
      alert("Select at least one loan type, or choose \"All loan types\".")
      return
    }

    setIsSaving(true)
    const payload: LoanRequirementPayload = {
      scenario: form.scenario.trim(),
      instruction: form.instruction.trim(),
      loan_types: form.applyToAll ? [] : form.selectedTypes,
      attachmentFile: form.attachmentFile,
      removeAttachment: form.removeAttachment,
    }
    const result = editingId ? await onUpdate(editingId, payload) : await onCreate(payload)
    setIsSaving(false)

    if (result.ok) {
      setIsModalOpen(false)
      onChanged()
    } else {
      alert(result.errorMessage ?? "Error saving requirement")
    }
  }

  async function handleDelete(requirement: LoanRequirement) {
    if (!confirm(`Delete the "${requirement.scenario}" requirement?`)) return
    const result = await onDelete(requirement.id)
    if (result.ok) {
      onChanged()
    } else {
      alert(result.errorMessage ?? "Error deleting requirement")
    }
  }

  function itemsForGroup(groupKey: string) {
    return (requirements ?? []).filter((r) =>
      groupKey === ALL_LOAN_TYPES_KEY ? r.loan_types.length === 0 : r.loan_types.includes(groupKey),
    )
  }

  if (isLoading) {
    return (
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-20" />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-4 text-sm text-destructive">
        <AlertCircle className="size-4 shrink-0" /> {error}
      </div>
    )
  }

  const activeGroup = GROUPS.find((g) => g.key === selectedGroup)

  return (
    <div className="space-y-4">
      {!activeGroup ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {GROUPS.map((group) => {
            const count = itemsForGroup(group.key).length
            return (
              <Card
                key={group.key}
                role="button"
                tabIndex={0}
                onClick={() => setSelectedGroup(group.key)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") setSelectedGroup(group.key)
                }}
                className="group cursor-pointer transition-colors hover:border-primary/50 hover:bg-accent/40"
              >
                <CardContent className="flex items-center gap-4 p-5">
                  <div className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <group.icon className="size-5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium">{group.label}</p>
                    <p className="text-xs text-muted-foreground">
                      {count} requirement{count === 1 ? "" : "s"}
                    </p>
                  </div>
                  <ChevronRight className="size-4 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                </CardContent>
              </Card>
            )
          })}
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setSelectedGroup(null)}
                aria-label="Back to loan types"
              >
                <ArrowLeft className="size-4" />
              </Button>
              <div className="flex items-center gap-2">
                <activeGroup.icon className="size-4 text-muted-foreground" />
                <h3 className="text-sm font-medium">{activeGroup.label}</h3>
              </div>
            </div>
            <Button onClick={() => openCreate(activeGroup.key)} className="gap-2">
              <Plus className="size-4" /> {addButtonLabel}
            </Button>
          </div>

          {itemsForGroup(activeGroup.key).length === 0 ? (
            <div className="rounded-md border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
              {emptyStateText}
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {itemsForGroup(activeGroup.key).map((requirement) => (
                <RequirementCard
                  key={requirement.id}
                  requirement={requirement}
                  onEdit={() => openEdit(requirement)}
                  onDelete={() => handleDelete(requirement)}
                />
              ))}
            </div>
          )}
        </div>
      )}

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingId ? "Edit Requirement" : "Add Requirement"}</DialogTitle>
            <DialogDescription>
              Define an instruction for the loan-processing agent, scoped to one or more loan types or
              all of them.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSave} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="requirement-scenario">Scenario</Label>
              <Input
                id="requirement-scenario"
                placeholder="e.g. Verify rural property eligibility"
                value={form.scenario}
                onChange={(e) => setForm((prev) => ({ ...prev, scenario: e.target.value }))}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="requirement-instruction">Instruction</Label>
              <Textarea
                id="requirement-instruction"
                placeholder="Describe exactly what the agent should do…"
                className="min-h-32"
                value={form.instruction}
                onChange={(e) => setForm((prev) => ({ ...prev, instruction: e.target.value }))}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="requirement-attachment">Attachment (optional)</Label>
              {form.existingAttachmentFilename && !form.attachmentFile ? (
                <div className="flex items-center justify-between gap-2 rounded-md border border-border px-3 py-2 text-sm">
                  <span className="flex min-w-0 items-center gap-1.5 truncate">
                    <Paperclip className="size-3.5 shrink-0 text-muted-foreground" />
                    {form.existingAttachmentFilename}
                  </span>
                  <button
                    type="button"
                    onClick={handleRemoveAttachment}
                    className="shrink-0 text-muted-foreground hover:text-destructive"
                    aria-label="Remove attachment"
                  >
                    <X className="size-4" />
                  </button>
                </div>
              ) : (
                <Input
                  key={fileInputKey}
                  id="requirement-attachment"
                  type="file"
                  onChange={handleFileChange}
                  accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg,.webp,.txt,.csv"
                />
              )}
              <p className="text-xs text-muted-foreground">
                For scenarios where the agent needs a reference file — a sample document, checklist, etc.
              </p>
            </div>
            <div className="space-y-2">
              <Label>Applies to</Label>
              <label className="flex items-center gap-2 text-sm">
                <Checkbox checked={form.applyToAll} onCheckedChange={(checked) => toggleAll(checked === true)} />
                All loan types
              </label>
              <div className="grid grid-cols-2 gap-2 rounded-md border border-border p-3">
                {LOAN_TYPES.map((type) => (
                  <label key={type} className="flex items-center gap-2 text-sm">
                    <Checkbox
                      checked={form.selectedTypes.includes(type)}
                      disabled={form.applyToAll}
                      onCheckedChange={(checked) => toggleType(type, checked === true)}
                    />
                    {LOAN_TYPE_META[type].label}
                  </label>
                ))}
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSaving}>
                {isSaving && <Loader2 className="size-4 animate-spin" />}
                Save
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function RequirementCard({
  requirement,
  onEdit,
  onDelete,
}: {
  requirement: LoanRequirement
  onEdit: () => void
  onDelete: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const isLong = requirement.instruction.length > 160

  return (
    <Card className="flex flex-col">
      <CardHeader className="flex-row items-start justify-between gap-3 space-y-0">
        <div className="flex min-w-0 items-start gap-3">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-muted">
            <ClipboardList className="size-4" />
          </div>
          <CardTitle className="min-w-0 truncate text-sm">{requirement.scenario}</CardTitle>
        </div>
        <div className="flex shrink-0 gap-1">
          <Button variant="outline" size="icon" onClick={onEdit} aria-label="Edit requirement">
            <Edit2 className="size-3.5" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="text-destructive hover:bg-destructive/10"
            onClick={onDelete}
            aria-label="Delete requirement"
          >
            <Trash2 className="size-3.5" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="flex-1 space-y-2">
        <p className={expanded ? "text-sm text-muted-foreground" : "text-sm text-muted-foreground line-clamp-3"}>
          {requirement.instruction}
        </p>
        {requirement.attachment_url && (
          <a
            href={requirement.attachment_url}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 text-xs text-primary hover:underline"
          >
            <Paperclip className="size-3" /> {requirement.attachment_filename}
          </a>
        )}
      </CardContent>
      {isLong && (
        <CardFooter>
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="flex items-center gap-1 text-xs font-medium text-primary hover:underline"
          >
            <ChevronDown className={`size-3 transition-transform ${expanded ? "rotate-180" : ""}`} />
            {expanded ? "Show less" : "Show more"}
          </button>
        </CardFooter>
      )}
    </Card>
  )
}
