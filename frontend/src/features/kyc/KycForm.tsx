import { useRef, useState } from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { AlertCircle, Loader2, Paperclip, Send, X } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { formatBytes } from "@/lib/utils"
import { loanTypeLabel } from "@/features/loans/loanTypeMeta"
import { kycService } from "@/services/kycService"
import type { KycApplicationDetail } from "@/types/api"
import { SelfieCapture } from "./SelfieCapture"

const GENDERS = ["male", "female", "other"] as const

const kycSchema = z.object({
  applicant_name: z.string().min(1, "Full name is required"),
  applicant_phone: z.string().min(1, "Phone number is required"),
  applicant_email: z.string().email("Enter a valid email").optional().or(z.literal("")),
  credit_score: z
    .string()
    .optional()
    .refine((v) => !v || (/^\d{3}$/.test(v) && Number(v) >= 300 && Number(v) <= 900), {
      message: "Enter a valid credit score between 300 and 900",
    }),
  loan_type: z.string().min(1, "Loan type is required"),
  date_of_birth: z.string().min(1, "Date of birth is required"),
  gender: z.enum(GENDERS, { message: "Select a gender" }),
  address: z.string().min(1, "Address is required"),
})
type KycFormValues = z.infer<typeof kycSchema>

const MAX_FILES = 20
const MAX_FILE_SIZE = 15 * 1024 * 1024

interface KycFormProps {
  token: string
  detail: KycApplicationDetail
  onSubmitted: (bankNotified: boolean, banksNotifiedCount: number, warning: string | null) => void
}

export function KycForm({ token, detail, onSubmitted }: KycFormProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [files, setFiles] = useState<File[]>([])
  const [fileError, setFileError] = useState<string | null>(null)
  const [selfieFile, setSelfieFile] = useState<File | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const form = useForm<KycFormValues>({
    resolver: zodResolver(kycSchema),
    defaultValues: {
      applicant_name: detail.applicant_name ?? "",
      applicant_phone: detail.applicant_phone ?? "",
      applicant_email: detail.applicant_email ?? "",
      credit_score: "",
      loan_type: detail.loan_type,
      date_of_birth: detail.date_of_birth ?? "",
      gender: (detail.gender as KycFormValues["gender"]) ?? undefined,
      address: detail.address ?? "",
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

  async function onSubmit(values: KycFormValues) {
    setSubmitError(null)

    if (!selfieFile) {
      setSubmitError("Please capture or upload a selfie photo before submitting.")
      return
    }

    setIsSubmitting(true)

    const formData = new FormData()
    formData.append("applicant_name", values.applicant_name)
    formData.append("applicant_phone", values.applicant_phone)
    if (values.applicant_email) formData.append("applicant_email", values.applicant_email)
    if (values.credit_score) formData.append("credit_score", values.credit_score)
    formData.append("loan_type", values.loan_type)
    formData.append("date_of_birth", values.date_of_birth)
    formData.append("gender", values.gender)
    formData.append("address", values.address)

    const allFiles = [selfieFile, ...files]
    const labels = ["Selfie", ...files.map(() => null)]
    allFiles.forEach((file) => formData.append("documents", file))
    formData.append("document_labels", JSON.stringify(labels))

    const result = await kycService.submitKyc(token, formData)
    setIsSubmitting(false)

    if (result.ok && result.data) {
      onSubmitted(result.data.bank_notified, result.data.banks_notified_count, result.data.bank_notification_warning)
    } else {
      setSubmitError(result.errorMessage ?? "Failed to submit KYC. Please try again.")
    }
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-4 sm:grid-cols-2">
      <div className="space-y-1.5 sm:col-span-2">
        <Label>Selfie photo</Label>
        <SelfieCapture file={selfieFile} onChange={setSelfieFile} />
      </div>

      <div className="space-y-1.5">
        <Label>Full name</Label>
        <Input placeholder="Your full name" {...form.register("applicant_name")} />
        {form.formState.errors.applicant_name && (
          <p className="text-xs text-destructive">{form.formState.errors.applicant_name.message}</p>
        )}
      </div>
      <div className="space-y-1.5">
        <Label>Phone number</Label>
        <Input placeholder="+91…" {...form.register("applicant_phone")} />
        {form.formState.errors.applicant_phone && (
          <p className="text-xs text-destructive">{form.formState.errors.applicant_phone.message}</p>
        )}
      </div>
      <div className="space-y-1.5">
        <Label>Email</Label>
        <Input placeholder="you@example.com" {...form.register("applicant_email")} />
        {form.formState.errors.applicant_email && (
          <p className="text-xs text-destructive">{form.formState.errors.applicant_email.message}</p>
        )}
      </div>
      <div className="space-y-1.5">
        <Label>Credit score</Label>
        <Input placeholder="e.g. 750" {...form.register("credit_score")} />
        <p className="text-xs text-muted-foreground">Self-reported, e.g. from CIBIL/Experian.</p>
        {form.formState.errors.credit_score && (
          <p className="text-xs text-destructive">{form.formState.errors.credit_score.message}</p>
        )}
      </div>
      <div className="space-y-1.5">
        <Label>Date of birth</Label>
        <Input type="date" {...form.register("date_of_birth")} />
        {form.formState.errors.date_of_birth && (
          <p className="text-xs text-destructive">{form.formState.errors.date_of_birth.message}</p>
        )}
      </div>
      <div className="space-y-1.5">
        <Label>Gender</Label>
        <Select
          value={form.watch("gender")}
          onValueChange={(value) =>
            form.setValue("gender", value as KycFormValues["gender"], { shouldValidate: true })
          }
        >
          <SelectTrigger>
            <SelectValue placeholder="Select gender" />
          </SelectTrigger>
          <SelectContent>
            {GENDERS.map((g) => (
              <SelectItem key={g} value={g}>
                {g.charAt(0).toUpperCase() + g.slice(1)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {form.formState.errors.gender && (
          <p className="text-xs text-destructive">{form.formState.errors.gender.message}</p>
        )}
      </div>
      <div className="space-y-1.5 sm:col-span-2">
        <Label>Address</Label>
        <Textarea rows={2} placeholder="Your current residential address" {...form.register("address")} />
        {form.formState.errors.address && (
          <p className="text-xs text-destructive">{form.formState.errors.address.message}</p>
        )}
      </div>
      <div className="space-y-1.5 sm:col-span-2">
        <Label>Loan type</Label>
        <Select
          value={form.watch("loan_type")}
          onValueChange={(value) => form.setValue("loan_type", value, { shouldValidate: true })}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select loan type" />
          </SelectTrigger>
          <SelectContent>
            {detail.loan_types.map((type) => (
              <SelectItem key={type} value={type}>
                {loanTypeLabel(type)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {form.formState.errors.loan_type && (
          <p className="text-xs text-destructive">{form.formState.errors.loan_type.message}</p>
        )}
      </div>

      <div className="space-y-1.5 sm:col-span-2">
        <Label>Documents</Label>
        <p className="text-xs text-muted-foreground">
          Include your Aadhaar card, driving license, and any other required documents below.
        </p>
        {detail.required_documents && (
          <p className="mb-2 rounded-md bg-muted/40 p-3 text-xs text-muted-foreground">
            {detail.required_documents}
          </p>
        )}

        <input ref={fileInputRef} type="file" multiple onChange={handleFileChange} className="hidden" />
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
              <Send className="size-4" /> Submit KYC
            </>
          )}
        </Button>
      </div>
    </form>
  )
}
