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

const VEHICLE_TYPES = ["new", "used"] as const
const VEHICLE_TYPE_LABELS: Record<(typeof VEHICLE_TYPES)[number], string> = {
  new: "New",
  used: "Used",
}

const CURRENT_YEAR = 2026
const VEHICLE_YEARS = Array.from({ length: 15 }, (_, i) => String(CURRENT_YEAR + 1 - i))

const LOAN_TERMS_MONTHS = ["12", "24", "36", "48", "60", "72"] as const

/** Field key -> human label for the lead detail page (see leads/LeadsPage.tsx). */
export const CAR_LOAN_FIELD_LABELS: Record<string, string> = {
  drivers_license_number: "Driver's License Number",
  employment_type: "Employment Type",
  employer_name: "Employer Name",
  job_title: "Job Title",
  employment_start_date: "Employment Start Date",
  annual_income: "Annual Income",
  monthly_income: "Monthly Income",
  down_payment_amount: "Down Payment Amount",
  existing_loan_emi_amount: "Existing Monthly Loan/EMI Amount",
  monthly_debt_payments: "Monthly Debt Payments",
  vehicle_type: "Vehicle Type",
  vehicle_make: "Make",
  vehicle_model: "Model",
  vehicle_year: "Year",
  purchase_price: "Purchase Price",
  dealer_name: "Dealer Name",
  loan_term_months: "Loan Term (Months)",
}

export const CAR_LOAN_FIELD_KEYS = Object.keys(CAR_LOAN_FIELD_LABELS)

const DL_RE = /^[A-Za-z0-9-]{5,20}$/

export const carLoanDetailsSchema = z.object({
  drivers_license_number: z
    .string()
    .min(1, "Driver's license number is required")
    .regex(DL_RE, "Enter a valid driver's license number"),

  employment_type: z.enum(EMPLOYMENT_TYPES, { message: "Select an employment type" }),
  employer_name: z.string().min(1, "Employer name is required"),
  job_title: z.string().min(1, "Job title is required"),
  employment_start_date: pastDate("Employment start date"),
  annual_income: requiredMoney("Annual income"),
  monthly_income: requiredMoney("Monthly income"),

  down_payment_amount: requiredMoney("Down payment amount"),
  existing_loan_emi_amount: requiredMoney("Existing loan/EMI amount"),
  monthly_debt_payments: requiredMoney("Monthly debt payments"),

  vehicle_type: z.enum(VEHICLE_TYPES, { message: "Select a vehicle type" }),
  vehicle_make: z.string().min(1, "Make is required"),
  vehicle_model: z.string().min(1, "Model is required"),
  vehicle_year: z.string().min(1, "Year is required"),
  purchase_price: requiredMoney("Purchase price"),
  dealer_name: z.string().min(1, "Dealer name is required"),
  loan_term_months: z.enum(LOAN_TERMS_MONTHS, { message: "Select a loan term" }),
})

export type CarLoanDetailsValues = z.infer<typeof carLoanDetailsSchema>

export function CarLoanDetailsStep({ form }: { form: UseFormReturn<any> }) {
  return (
    <div className="animate-step space-y-6">
      <DetailsStepHeader
        title="Car loan details"
        description="A few more details our partner banks require for a car loan."
      />

      <div className="space-y-3">
        <SectionHeading>Personal Information</SectionHeading>
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField
            form={form}
            name="drivers_license_number"
            label="Driver's License Number"
            placeholder="DL-1234567890"
          />
        </div>
      </div>

      <div className="space-y-3 border-t border-border pt-5">
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
          <MoneyField form={form} name="down_payment_amount" label="Down Payment Amount" placeholder="100000" />
          <MoneyField
            form={form}
            name="existing_loan_emi_amount"
            label="Existing Monthly Loan/EMI Amount"
            placeholder="10000"
          />
          <MoneyField form={form} name="monthly_debt_payments" label="Monthly Debt Payments" placeholder="15000" />
        </div>
      </div>

      <div className="space-y-3 border-t border-border pt-5">
        <SectionHeading>Vehicle Information</SectionHeading>
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField
            form={form}
            name="vehicle_type"
            label="Vehicle Type"
            options={VEHICLE_TYPES}
            labels={VEHICLE_TYPE_LABELS}
          />
          <SelectField
            form={form}
            name="vehicle_year"
            label="Year"
            options={VEHICLE_YEARS}
            labels={Object.fromEntries(VEHICLE_YEARS.map((y) => [y, y]))}
          />
          <TextField form={form} name="vehicle_make" label="Make" placeholder="Maruti Suzuki" />
          <TextField form={form} name="vehicle_model" label="Model" placeholder="Swift" />
          <MoneyField form={form} name="purchase_price" label="Purchase Price" placeholder="800000" />
          <TextField form={form} name="dealer_name" label="Dealer Name" placeholder="City Motors" />
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
