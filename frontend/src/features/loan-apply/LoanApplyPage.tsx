import { useMemo, useState } from "react"
import { useLocation, useNavigate, useSearchParams } from "react-router-dom"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { ArrowLeft, CheckCircle2, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"
import { LOAN_TYPE_META, LOAN_TYPES } from "@/features/loans/loanTypeMeta"
import type { LoanType } from "@/types/api"
import { loanApplyService } from "@/services/loanApplyService"
import { SSN_RE, PHONE_RE } from "./LoanFieldPrimitives"
import { HOME_LOAN_FIELD_KEYS, HomeLoanDetailsStep, homeLoanDetailsSchema } from "./HomeLoanDetailsStep"
import {
  PERSONAL_LOAN_FIELD_KEYS,
  PersonalLoanDetailsStep,
  personalLoanDetailsSchema,
} from "./PersonalLoanDetailsStep"
import { CAR_LOAN_FIELD_KEYS, CarLoanDetailsStep, carLoanDetailsSchema } from "./CarLoanDetailsStep"
import {
  EDUCATION_LOAN_FIELD_KEYS,
  EducationLoanDetailsStep,
  educationLoanDetailsSchema,
} from "./EducationLoanDetailsStep"
import { GOLD_LOAN_FIELD_KEYS, GoldLoanDetailsStep, goldLoanDetailsSchema } from "./GoldLoanDetailsStep"
import {
  listSavedApplicants,
  saveApplicant,
  savedApplicantLabel,
  type SavedApplicant,
} from "./savedApplicants"

/** Larger control sizing for this page only — see LoanFieldPrimitives.tsx for the matching per-loan-type override. */
const FIELD_SIZE = "h-14 px-4 text-lg"
const TEXTAREA_SIZE = "min-h-28 px-4 py-3 text-lg"

const GENDERS = ["male", "female", "other"] as const
const CITIZENSHIP_STATUSES = ["citizen", "permanent_resident", "visa_holder", "other"] as const
const MARITAL_STATUSES = ["single", "married", "divorced", "widowed"] as const

const CITIZENSHIP_LABELS: Record<(typeof CITIZENSHIP_STATUSES)[number], string> = {
  citizen: "Citizen",
  permanent_resident: "Permanent Resident",
  visa_holder: "Visa Holder",
  other: "Other",
}

const MARITAL_STATUS_LABELS: Record<(typeof MARITAL_STATUSES)[number], string> = {
  single: "Single",
  married: "Married",
  divorced: "Divorced",
  widowed: "Widowed",
}

/**
 * Every loan type now has its own dedicated details form (fields specific to
 * that loan, organized into sections) — see the *DetailsStep.tsx siblings in
 * this folder. Fields already collected in the base form above (name, email,
 * phone, DOB, SSN, gender, citizenship, current address, marital status,
 * FICO score, loan amount, ZIP) are intentionally NOT repeated in any of
 * them, even though some loan types used to ask for one or both of them
 * individually before they were hoisted up here.
 */
const LOAN_TYPE_DETAILS: Record<
  LoanType,
  { fieldKeys: string[]; schema: z.ZodTypeAny; Component: (props: { form: any }) => React.JSX.Element }
> = {
  home_loan: { fieldKeys: HOME_LOAN_FIELD_KEYS, schema: homeLoanDetailsSchema, Component: HomeLoanDetailsStep },
  personal_loan: {
    fieldKeys: PERSONAL_LOAN_FIELD_KEYS,
    schema: personalLoanDetailsSchema,
    Component: PersonalLoanDetailsStep,
  },
  car_loan: { fieldKeys: CAR_LOAN_FIELD_KEYS, schema: carLoanDetailsSchema, Component: CarLoanDetailsStep },
  education_loan: {
    fieldKeys: EDUCATION_LOAN_FIELD_KEYS,
    schema: educationLoanDetailsSchema,
    Component: EducationLoanDetailsStep,
  },
  gold_loan: { fieldKeys: GOLD_LOAN_FIELD_KEYS, schema: goldLoanDetailsSchema, Component: GoldLoanDetailsStep },
}

const baseSchema = z.object({
  first_name: z.string().min(1, "First name is required"),
  last_name: z.string().min(1, "Last name is required"),
  email: z.string().email("Enter a valid email"),
  phone_number: z.string().min(1, "Phone number is required").regex(PHONE_RE, "Enter a valid 10-digit phone number"),
  date_of_birth: z
    .string()
    .min(1, "Date of birth is required")
    .refine((v) => !isNaN(new Date(v).getTime()), { message: "Enter a valid date" })
    .refine(
      (v) => (Date.now() - new Date(v).getTime()) / (365.25 * 24 * 60 * 60 * 1000) >= 18,
      { message: "Applicant must be at least 18 years old" },
    ),
  ssn: z.string().min(1, "SSN is required").regex(SSN_RE, "Enter a valid SSN (e.g. 123-45-6789)"),
  gender: z.enum(GENDERS, { message: "Select a gender" }),
  citizenship_status: z.enum(CITIZENSHIP_STATUSES, { message: "Select a citizenship status" }),
  current_address: z.string().min(1, "Current address is required"),
  marital_status: z.enum(MARITAL_STATUSES, { message: "Select a marital status" }),
  fico_score: z
    .string()
    .min(1, "FICO score is required")
    .refine((v) => /^\d{3}$/.test(v) && Number(v) >= 300 && Number(v) <= 850, {
      message: "Enter a valid FICO score between 300 and 850",
    }),
  loan_type: z.string().min(1, "Loan type is required"),
  loan_amount: z
    .string()
    .min(1, "Loan amount is required")
    .refine((v) => !isNaN(Number(v)) && Number(v) > 0, {
      message: "Enter a valid loan amount",
    }),
  zip_code: z.string().min(1, "ZIP code is required"),
  extra_loan_details: z.record(z.string(), z.string()).optional(),
})

type LoanApplyValues = z.infer<typeof baseSchema>

const EMPTY_DEFAULTS = {
  first_name: "",
  last_name: "",
  email: "",
  phone_number: "",
  date_of_birth: "",
  ssn: "",
  gender: undefined,
  citizenship_status: undefined,
  current_address: "",
  marital_status: undefined,
  fico_score: "",
  loan_type: "",
  loan_amount: "",
  zip_code: "",
  extra_loan_details: {},
} as const

export function LoanApplyPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const location = useLocation()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitted, setSubmitted] = useState(false)
  const [submittedName, setSubmittedName] = useState("")
  const [savedApplicants] = useState<SavedApplicant[]>(() => listSavedApplicants())

  // location.key is "default" only for the very first history entry (a
  // fresh page load / directly-typed URL) — anything reached by navigating
  // within the app (e.g. Loans -> pick bank -> Apply) gets a generated key,
  // so going back with navigate(-1) lands somewhere real instead of leaving
  // the app. Falls back to the dashboard for the direct-link/public case.
  const canGoBack = location.key !== "default"
  function handleBack() {
    if (canGoBack) navigate(-1)
    else navigate("/")
  }

  // Lets the Loans sidebar flow (pick a category, compare banks, hit Apply)
  // deep-link here with the loan type already chosen — the applicant still
  // fills out this one form, which notifies every bank offering that loan
  // type (see loan_apply/routes.py), not just the bank they were viewing.
  const initialLoanType = LOAN_TYPES.includes(searchParams.get("loan_type") as LoanType)
    ? (searchParams.get("loan_type") as LoanType)
    : ""

  const schema = useMemo(() => {
    return baseSchema.superRefine((data, ctx) => {
      const details = LOAN_TYPE_DETAILS[data.loan_type as LoanType]
      if (!details) return
      const result = details.schema.safeParse(data.extra_loan_details ?? {})
      if (!result.success) {
        for (const issue of result.error.issues) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ["extra_loan_details", ...issue.path],
            message: issue.message,
          })
        }
      }
    })
  }, [])

  const form = useForm<LoanApplyValues>({
    resolver: zodResolver(schema),
    mode: "onChange",
    defaultValues: { ...EMPTY_DEFAULTS, loan_type: initialLoanType } as unknown as LoanApplyValues,
  })

  const errors = form.formState.errors
  const selectedLoanType = form.watch("loan_type") as LoanType | ""
  const selectedDetails = selectedLoanType ? LOAN_TYPE_DETAILS[selectedLoanType] : undefined

  /**
   * Fired when the First Name field's value matches a saved applicant's
   * datalist label exactly (see the <datalist> below) — fills every field
   * from that saved submission except ssn (never saved, see
   * savedApplicants.ts) and first_name itself (already what the user typed/
   * picked, and may legitimately differ in casing from the saved value).
   */
  function applySavedApplicant(applicant: SavedApplicant) {
    form.reset({
      ...EMPTY_DEFAULTS,
      ...applicant,
      ssn: "",
    } as unknown as LoanApplyValues)
    form.trigger()
  }

  function handleFirstNameChange(rawValue: string) {
    const match = savedApplicants.find((a) => savedApplicantLabel(a) === rawValue)
    if (match) {
      applySavedApplicant(match)
    } else {
      form.setValue("first_name", rawValue, { shouldValidate: true })
    }
  }

  async function onSubmit(values: LoanApplyValues) {
    setSubmitError(null)
    setIsSubmitting(true)

    const activeFields = LOAN_TYPE_DETAILS[values.loan_type as LoanType]?.fieldKeys ?? []
    const filteredExtraDetails: Record<string, string> = {}
    if (values.extra_loan_details) {
      for (const field of activeFields) {
        filteredExtraDetails[field] = values.extra_loan_details[field] || ""
      }
    }

    const result = await loanApplyService.submit({
      ...values,
      fico_score: Number(values.fico_score),
      loan_amount: Number(values.loan_amount),
      extra_loan_details: filteredExtraDetails,
    })

    setIsSubmitting(false)

    if (result.ok && result.data) {
      const { ssn: _ssn, ...withoutSsn } = values
      saveApplicant({ ...withoutSsn, extra_loan_details: filteredExtraDetails })
      setSubmittedName(values.first_name)
      setSubmitted(true)
      form.reset(EMPTY_DEFAULTS as unknown as LoanApplyValues)
      window.scrollTo({ top: 0, behavior: "smooth" })
    } else {
      setSubmitError(result.errorMessage ?? "Failed to submit the form. Please try again.")
    }
  }

  return (
    <div className="min-h-svh bg-background">
      <div className="relative border-b border-border bg-muted/40 py-12 text-center">
        <Button
          type="button"
          variant="ghost"
          onClick={handleBack}
          className="absolute left-4 top-1/2 -translate-y-1/2 sm:left-6"
        >
          <ArrowLeft className="size-4" /> Back
        </Button>
        <h1 className="text-3xl font-bold text-foreground sm:text-4xl">Apply for a loan</h1>
      </div>

      <div className="mx-auto max-w-2xl px-6 py-12">
        {submitted ? (
          <SuccessPanel name={submittedName} onReset={() => setSubmitted(false)} />
        ) : (
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-7">
            <Field
              label="First Name"
              caption={
                savedApplicants.length > 0
                  ? "Pick a saved name below to prefill the rest of the form."
                  : undefined
              }
              error={errors.first_name?.message}
            >
              <Input
                className={FIELD_SIZE}
                list="saved-applicants"
                {...form.register("first_name")}
                onChange={(e) => handleFirstNameChange(e.target.value)}
              />
              <datalist id="saved-applicants">
                {savedApplicants.map((applicant) => (
                  <option key={applicant.email} value={savedApplicantLabel(applicant)} />
                ))}
              </datalist>
            </Field>

            <Field label="Last Name" error={errors.last_name?.message}>
              <Input className={FIELD_SIZE} {...form.register("last_name")} />
            </Field>

            <Field label="Email" error={errors.email?.message}>
              <Input className={FIELD_SIZE} type="email" {...form.register("email")} />
            </Field>

            <Field label="Phone Number" error={errors.phone_number?.message}>
              <Input
                className={FIELD_SIZE}
                type="tel"
                placeholder="9876543210"
                {...form.register("phone_number")}
              />
            </Field>

            <Field label="Date of Birth" error={errors.date_of_birth?.message}>
              <Input className={FIELD_SIZE} type="date" {...form.register("date_of_birth")} />
            </Field>

            <Field label="Social Security Number" error={errors.ssn?.message}>
              <Input className={FIELD_SIZE} placeholder="123-45-6789" {...form.register("ssn")} />
            </Field>

            <Field label="Gender" error={errors.gender?.message}>
              <Select
                value={form.watch("gender")}
                onValueChange={(value) => form.setValue("gender", value as any, { shouldValidate: true })}
              >
                <SelectTrigger className={cn("rounded-md border-input shadow-none", FIELD_SIZE)}>
                  <SelectValue placeholder="Please Select" />
                </SelectTrigger>
                <SelectContent>
                  {GENDERS.map((g) => (
                    <SelectItem key={g} value={g}>
                      {g.charAt(0).toUpperCase() + g.slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>

            <Field label="Citizenship Status" error={errors.citizenship_status?.message}>
              <Select
                value={form.watch("citizenship_status")}
                onValueChange={(value) =>
                  form.setValue("citizenship_status", value as any, { shouldValidate: true })
                }
              >
                <SelectTrigger className={cn("rounded-md border-input shadow-none", FIELD_SIZE)}>
                  <SelectValue placeholder="Please Select" />
                </SelectTrigger>
                <SelectContent>
                  {CITIZENSHIP_STATUSES.map((c) => (
                    <SelectItem key={c} value={c}>
                      {CITIZENSHIP_LABELS[c]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>

            <Field label="Current Address" error={errors.current_address?.message}>
              <Textarea
                className={TEXTAREA_SIZE}
                placeholder="Street, city, state, ZIP"
                {...form.register("current_address")}
              />
            </Field>

            <Field label="Marital Status" error={errors.marital_status?.message}>
              <Select
                value={form.watch("marital_status")}
                onValueChange={(value) => form.setValue("marital_status", value as any, { shouldValidate: true })}
              >
                <SelectTrigger className={cn("rounded-md border-input shadow-none", FIELD_SIZE)}>
                  <SelectValue placeholder="Please Select" />
                </SelectTrigger>
                <SelectContent>
                  {MARITAL_STATUSES.map((m) => (
                    <SelectItem key={m} value={m}>
                      {MARITAL_STATUS_LABELS[m]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>

            <Field
              label="FICO Score"
              caption="Please enter your estimated FICO score"
              error={errors.fico_score?.message}
            >
              <Input className={FIELD_SIZE} {...form.register("fico_score")} />
            </Field>

            <Field label="Loan Type" error={errors.loan_type?.message}>
              <Select
                value={selectedLoanType}
                onValueChange={(value) => {
                  form.setValue("loan_type", value, { shouldValidate: true })
                  form.setValue("extra_loan_details", {}, { shouldValidate: true })
                }}
              >
                <SelectTrigger className={cn("rounded-md border-input shadow-none", FIELD_SIZE)}>
                  <SelectValue placeholder="Please Select" />
                </SelectTrigger>
                <SelectContent>
                  {LOAN_TYPES.map((type) => (
                    <SelectItem key={type} value={type}>
                      {LOAN_TYPE_META[type].label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>

            <Field label="Loan Amount" error={errors.loan_amount?.message}>
              <div className="relative">
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                <Input
                  className={`${FIELD_SIZE} pl-8`}
                  type="number"
                  min={0}
                  placeholder="e.g. 500000"
                  {...form.register("loan_amount")}
                />
              </div>
            </Field>

            <Field label="ZIP Code" error={errors.zip_code?.message}>
              <Input className={FIELD_SIZE} {...form.register("zip_code")} />
            </Field>

            {/* Fields below change based on the loan type selected above. */}
            {selectedDetails && (
              <div className="border-t border-border pt-7">
                <selectedDetails.Component form={form} />
              </div>
            )}

            {submitError && (
              <div className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                {submitError}
              </div>
            )}

            <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 className="size-4 animate-spin" /> Submitting…
                </>
              ) : (
                "Submit application"
              )}
            </Button>
          </form>
        )}
      </div>
    </div>
  )
}

function Field({
  label,
  caption,
  error,
  children,
}: {
  label: string
  caption?: string
  error?: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs font-bold uppercase tracking-wide text-foreground">
        {label}
        <span className="text-destructive">*</span>
      </Label>
      {caption && <p className="text-sm text-muted-foreground">{caption}</p>}
      {children}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}

function SuccessPanel({ name, onReset }: { name: string; onReset: () => void }) {
  return (
    <div className="flex flex-col items-center gap-4 py-16 text-center">
      <div className="flex size-16 items-center justify-center rounded-full bg-success/15 text-success">
        <CheckCircle2 className="size-8" />
      </div>
      <div>
        <h3 className="text-xl font-semibold">{name ? `Thanks, ${name}.` : "You're all set."}</h3>
        <p className="mt-2 max-w-sm text-sm text-muted-foreground">
          Your application is in. We're matching it with partner banks now — you'll hear back by email
          shortly.
        </p>
      </div>
      <Button variant="outline" onClick={onReset} className="mt-2">
        Submit another application
      </Button>
    </div>
  )
}
