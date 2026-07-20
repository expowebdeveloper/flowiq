import { z } from "zod"
import type { UseFormReturn } from "react-hook-form"

import {
  DetailsStepHeader,
  EMPLOYMENT_TYPES,
  EMPLOYMENT_TYPE_LABELS,
  MoneyField,
  SectionHeading,
  SelectField,
  TextField,
  requiredMoney,
} from "./LoanFieldPrimitives"

const GOLD_TYPES = ["jewelry", "coin", "bar"] as const
const GOLD_TYPE_LABELS: Record<(typeof GOLD_TYPES)[number], string> = {
  jewelry: "Jewelry",
  coin: "Coin",
  bar: "Bar",
}

const GOLD_PURITIES = ["24k", "22k", "18k", "14k"] as const
const GOLD_PURITY_LABELS: Record<(typeof GOLD_PURITIES)[number], string> = {
  "24k": "24 Karat",
  "22k": "22 Karat",
  "18k": "18 Karat",
  "14k": "14 Karat",
}

const LOAN_PURPOSES = [
  "business",
  "medical_expenses",
  "agriculture",
  "wedding",
  "education",
  "debt_consolidation",
  "other",
] as const
const LOAN_PURPOSE_LABELS: Record<(typeof LOAN_PURPOSES)[number], string> = {
  business: "Business",
  medical_expenses: "Medical Expenses",
  agriculture: "Agriculture",
  wedding: "Wedding",
  education: "Education",
  debt_consolidation: "Debt Consolidation",
  other: "Other",
}

const LOAN_TERMS_MONTHS = ["3", "6", "12", "24", "36"] as const

/** Field key -> human label for the lead detail page (see leads/LeadsPage.tsx). */
export const GOLD_LOAN_FIELD_LABELS: Record<string, string> = {
  employment_type: "Employment Type",
  employer_name: "Employer Name",
  annual_income: "Annual Income",
  gold_type: "Gold Type",
  gold_purity_karat: "Gold Purity",
  gold_weight_grams: "Approximate Gold Weight (Grams)",
  estimated_gold_value: "Estimated Gold Value",
  loan_purpose: "Loan Purpose",
  loan_term_months: "Loan Term (Months)",
}

export const GOLD_LOAN_FIELD_KEYS = Object.keys(GOLD_LOAN_FIELD_LABELS)

export const goldLoanDetailsSchema = z.object({
  employment_type: z.enum(EMPLOYMENT_TYPES, { message: "Select an employment type" }),
  employer_name: z.string().min(1, "Employer name is required"),
  annual_income: requiredMoney("Annual income"),

  gold_type: z.enum(GOLD_TYPES, { message: "Select a gold type" }),
  gold_purity_karat: z.enum(GOLD_PURITIES, { message: "Select gold purity" }),
  gold_weight_grams: z
    .string()
    .min(1, "Gold weight is required")
    .refine((v) => !isNaN(Number(v)) && Number(v) > 0, { message: "Enter a valid weight in grams" }),
  estimated_gold_value: requiredMoney("Estimated gold value"),

  loan_purpose: z.enum(LOAN_PURPOSES, { message: "Select a loan purpose" }),
  loan_term_months: z.enum(LOAN_TERMS_MONTHS, { message: "Select a loan term" }),
})

export type GoldLoanDetailsValues = z.infer<typeof goldLoanDetailsSchema>

export function GoldLoanDetailsStep({ form }: { form: UseFormReturn<any> }) {
  return (
    <div className="animate-step space-y-6">
      <DetailsStepHeader
        title="Gold loan details"
        description="A few more details our partner banks require for a gold loan."
      />

      <div className="space-y-3">
        <SectionHeading>Employment Information</SectionHeading>
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField
            form={form}
            name="employment_type"
            label="Employment Type"
            options={EMPLOYMENT_TYPES}
            labels={EMPLOYMENT_TYPE_LABELS}
          />
          <TextField form={form} name="employer_name" label="Employer Name" placeholder="Acme Inc." />
          <MoneyField form={form} name="annual_income" label="Annual Income" placeholder="600000" />
        </div>
      </div>

      <div className="space-y-3 border-t border-border pt-5">
        <SectionHeading>Gold Details</SectionHeading>
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField
            form={form}
            name="gold_type"
            label="Gold Type"
            options={GOLD_TYPES}
            labels={GOLD_TYPE_LABELS}
          />
          <SelectField
            form={form}
            name="gold_purity_karat"
            label="Gold Purity"
            options={GOLD_PURITIES}
            labels={GOLD_PURITY_LABELS}
          />
          <TextField
            form={form}
            name="gold_weight_grams"
            label="Approximate Gold Weight (Grams)"
            type="number"
            placeholder="50"
          />
          <MoneyField form={form} name="estimated_gold_value" label="Estimated Gold Value" placeholder="300000" />
        </div>
      </div>

      <div className="space-y-3 border-t border-border pt-5">
        <SectionHeading>Loan Information</SectionHeading>
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField
            form={form}
            name="loan_purpose"
            label="Loan Purpose"
            options={LOAN_PURPOSES}
            labels={LOAN_PURPOSE_LABELS}
          />
          <SelectField
            form={form}
            name="loan_term_months"
            label="Loan Term (Months)"
            options={LOAN_TERMS_MONTHS}
            labels={Object.fromEntries(LOAN_TERMS_MONTHS.map((t) => [t, `${t} months`]))}
          />
        </div>
      </div>
    </div>
  )
}
