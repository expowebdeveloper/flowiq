import { useRef, useState } from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { AlertCircle, ArrowLeft, Loader2, Paperclip, Send, X } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { useAuth } from "@/contexts/AuthContext"
import { formatBytes } from "@/lib/utils"
import { banksService } from "@/services/banksService"
import type { BankLoanRate } from "@/types/api"
import { loanTypeLabel } from "./loanTypeMeta"

const applicationSchema = z.object({
  applicant_name: z.string().min(1, "Full name is required"),
  applicant_phone: z.string().min(1, "Phone number is required"),
  applicant_email: z.string().email("Enter a valid email").optional().or(z.literal("")),
  notes: z.string().optional(),
})
type ApplicationForm = z.infer<typeof applicationSchema>

const MAX_FILES = 20
const MAX_FILE_SIZE = 15 * 1024 * 1024

interface ApplyFormProps {
  rate: BankLoanRate
  onBack: () => void
  onSubmitted: (applicationId: string) => void
}

export function ApplyForm({ rate, onBack, onSubmitted }: ApplyFormProps) {
  const { email: sessionEmail } = useAuth()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [files, setFiles] = useState<File[]>([])
  const [fileError, setFileError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const form = useForm<ApplicationForm>({
    resolver: zodResolver(applicationSchema),
    defaultValues: {
      applicant_name: "",
      applicant_phone: "",
      applicant_email: sessionEmail ?? "",
      notes: "",
    },
  })

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = Array.from(e.target.files ?? [])
    if (selected.length > MAX_FILES) {
      setFileError(`Maximum ${MAX_FILES} files allowed`)
      return
    }
    const oversized = selected.find((f) => f.size > MAX_FILE_SIZE)
    if (oversized) {
      setFileError(`"${oversized.name}" exceeds the 15MB limit`)
      return
    }
    setFileError(null)
    setFiles(selected)
  }

  function removeFile(index: number) {
    setFiles((prev) => prev.filter((_, i) => i !== index))
  }

  async function onSubmit(values: ApplicationForm) {
    setSubmitError(null)
    setIsSubmitting(true)

    const formData = new FormData()
    formData.append("bank_loan_rate_id", rate.id)
    formData.append("applicant_name", values.applicant_name)
    formData.append("applicant_phone", values.applicant_phone)
    if (values.applicant_email) formData.append("applicant_email", values.applicant_email)
    if (values.notes) formData.append("notes", values.notes)
    files.forEach((file) => formData.append("documents", file))

    const result = await banksService.submitApplication(formData)
    setIsSubmitting(false)

    if (result.ok && result.data) {
      onSubmitted(result.data.id)
    } else {
      setSubmitError(result.errorMessage ?? "Failed to submit application. Please try again.")
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={onBack} aria-label="Back to bank list">
          <ArrowLeft className="size-4" />
        </Button>
        <h3 className="text-sm font-medium">
          Apply — {rate.bank_name} · {loanTypeLabel(rate.loan_type)}
        </h3>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{rate.bank_name}</CardTitle>
          <CardDescription>{rate.interest_rate}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>Full name</Label>
              <Input placeholder="Applicant's full name" {...form.register("applicant_name")} />
              {form.formState.errors.applicant_name && (
                <p className="text-xs text-destructive">
                  {form.formState.errors.applicant_name.message}
                </p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label>Phone number</Label>
              <Input placeholder="+91…" {...form.register("applicant_phone")} />
              {form.formState.errors.applicant_phone && (
                <p className="text-xs text-destructive">
                  {form.formState.errors.applicant_phone.message}
                </p>
              )}
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <Label>Email (optional)</Label>
              <Input placeholder="applicant@example.com" {...form.register("applicant_email")} />
              {form.formState.errors.applicant_email && (
                <p className="text-xs text-destructive">
                  {form.formState.errors.applicant_email.message}
                </p>
              )}
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <Label>Notes (optional)</Label>
              <Textarea rows={3} placeholder="Anything the bank should know…" {...form.register("notes")} />
            </div>

            <div className="space-y-1.5 sm:col-span-2">
              <Label>
                Required documents
                {rate.required_documents_list.length > 0 && (
                  <span className="ml-1 font-normal text-muted-foreground">
                    ({rate.required_documents_list.length} listed by the bank)
                  </span>
                )}
              </Label>

              {rate.required_documents_list.length > 0 && (
                <ul className="mb-2 space-y-1 rounded-md bg-muted/40 p-3">
                  {rate.required_documents_list.map((doc, i) => (
                    <li key={i} className="flex gap-1.5 text-xs text-muted-foreground">
                      <Badge variant="outline" className="h-fit shrink-0 px-1 py-0 text-[10px]">
                        {i + 1}
                      </Badge>
                      {doc}
                    </li>
                  ))}
                </ul>
              )}

              <input
                ref={fileInputRef}
                type="file"
                multiple
                onChange={handleFileChange}
                className="hidden"
              />
              <Button type="button" variant="outline" onClick={() => fileInputRef.current?.click()}>
                <Paperclip className="size-4" /> Upload documents
              </Button>
              {fileError && <p className="text-xs text-destructive">{fileError}</p>}
              {files.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {files.map((file, i) => (
                    <li
                      key={`${file.name}-${i}`}
                      className="flex items-center justify-between rounded-md border border-border px-2.5 py-1.5 text-xs"
                    >
                      <span className="truncate">{file.name}</span>
                      <span className="ml-2 flex shrink-0 items-center gap-2 text-muted-foreground">
                        <Badge variant="secondary">{formatBytes(file.size)}</Badge>
                        <button
                          type="button"
                          onClick={() => removeFile(i)}
                          className="text-muted-foreground hover:text-destructive"
                        >
                          <X className="size-3.5" />
                        </button>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {submitError && (
              <div className="flex items-start gap-2 rounded-md bg-destructive/10 p-3 text-sm text-destructive sm:col-span-2">
                <AlertCircle className="mt-0.5 size-4 shrink-0" />
                <span>{submitError}</span>
              </div>
            )}

            <div className="sm:col-span-2">
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="size-4 animate-spin" /> Submitting…
                  </>
                ) : (
                  <>
                    <Send className="size-4" /> Submit application
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
