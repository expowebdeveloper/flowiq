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
  pastDate,
  requiredMoney,
} from "./LoanFieldPrimitives"

const LOAN_PURPOSES = [
  "debt_consolidation",
  "medical_expenses",
  "home_improvement",
  "wedding",
  "travel",
  "education",
  "other",
] as const
const LOAN_PURPOSE_LABELS: Record<(typeof LOAN_PURPOSES)[number], string> = {
  debt_consolidation: "Debt Consolidation",
  medical_expenses: "Medical Expenses",
  home_improvement: "Home Improvement",
  wedding: "Wedding",
  travel: "Travel",
  education: "Education",
  other: "Other",
}

const LOAN_TERMS_MONTHS = ["12", "24", "36", "48", "60"] as const

/** Field key -> human label for the lead detail page (see leads/LeadsPage.tsx). */
export const PERSONAL_LOAN_FIELD_LABELS: Record<string, string> = {
  employment_type: "Employment Type",
  employer_name: "Employer Name",
  job_title: "Job Title",
  employment_start_date: "Employment Start Date",
  annual_income: "Annual Income",
  monthly_income: "Monthly Income",
  existing_loan_emi_amount: "Existing Monthly Loan/EMI Amount",
  monthly_debt_payments: "Monthly Debt Payments",
  loan_purpose: "Loan Purpose",
  loan_term_months: "Loan Term (Months)",
}

export const PERSONAL_LOAN_FIELD_KEYS = Object.keys(PERSONAL_LOAN_FIELD_LABELS)

export const personalLoanDetailsSchema = z.object({
  employment_type: z.enum(EMPLOYMENT_TYPES, { message: "Select an employment type" }),
  employer_name: z.string().min(1, "Employer name is required"),
  job_title: z.string().min(1, "Job title is required"),
  employment_start_date: pastDate("Employment start date"),
  annual_income: requiredMoney("Annual income"),
  monthly_income: requiredMoney("Monthly income"),

  existing_loan_emi_amount: requiredMoney("Existing loan/EMI amount"),
  monthly_debt_payments: requiredMoney("Monthly debt payments"),
  loan_purpose: z.enum(LOAN_PURPOSES, { message: "Select a loan purpose" }),
  loan_term_months: z.enum(LOAN_TERMS_MONTHS, { message: "Select a loan term" }),
})

export type PersonalLoanDetailsValues = z.infer<typeof personalLoanDetailsSchema>

export function PersonalLoanDetailsStep({ form }: { form: UseFormReturn<any> }) {
  return (
    <div className="animate-step space-y-6">
      <DetailsStepHeader
        title="Personal loan details"
        description="A few more details our partner banks require for a personal loan."
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
          <TextField form={form} name="job_title" label="Job Title" placeholder="Software Engineer" />
          <TextField form={form} name="employment_start_date" label="Employment Start Date" type="date" />
          <MoneyField form={form} name="annual_income" label="Annual Income" placeholder="1200000" />
          <MoneyField form={form} name="monthly_income" label="Monthly Income" placeholder="100000" />
        </div>
      </div>

      <div className="space-y-3 border-t border-border pt-5">
        <SectionHeading>Financial Information</SectionHeading>
        <div className="grid gap-4 sm:grid-cols-2">
          <MoneyField
            form={form}
            name="existing_loan_emi_amount"
            label="Existing Monthly Loan/EMI Amount"
            placeholder="10000"
          />
          <MoneyField form={form} name="monthly_debt_payments" label="Monthly Debt Payments" placeholder="15000" />
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
