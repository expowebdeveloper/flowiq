import { z } from "zod"
import type { UseFormReturn } from "react-hook-form"

import {
  DetailsStepHeader,
  EMPLOYMENT_TYPES,
  EMPLOYMENT_TYPE_LABELS,
  MoneyField,
  SectionHeading,
  SelectField,
  TextAreaField,
  TextField,
  pastDate,
  requiredMoney,
} from "./LoanFieldPrimitives"

const PROPERTY_TYPES = ["single_family", "condo", "townhouse", "multi_family", "other"] as const
const LOAN_TERMS = ["10", "15", "20", "25", "30"] as const
const OCCUPANCY_TYPES = ["primary_residence", "secondary_home", "investment_property"] as const

const PROPERTY_TYPE_LABELS: Record<(typeof PROPERTY_TYPES)[number], string> = {
  single_family: "Single-Family Home",
  condo: "Condominium",
  townhouse: "Townhouse",
  multi_family: "Multi-Family",
  other: "Other",
}

const OCCUPANCY_TYPE_LABELS: Record<(typeof OCCUPANCY_TYPES)[number], string> = {
  primary_residence: "Primary Residence",
  secondary_home: "Secondary Home",
  investment_property: "Investment Property",
}

/**
 * Field key -> human label, used to render this step's answers on the lead
 * detail page (see leads/LeadsPage.tsx). Kept separate from json/require.json,
 * which also drives the unrelated /verify-json tool's own validation.
 * date_of_birth/ssn/current_address/marital_status are NOT here — those live
 * in the base form's shared fields (see LoanApplyPage.tsx), asked once
 * regardless of loan type, not duplicated per loan type.
 */
export const HOME_LOAN_FIELD_LABELS: Record<string, string> = {
  employment_type: "Employment Type",
  employer_name: "Employer Name",
  job_title: "Job Title",
  employment_start_date: "Employment Start Date",
  annual_income: "Annual Income",
  monthly_income: "Monthly Income",
  monthly_debt_payments: "Monthly Debt Payments",
  existing_loan_emi_amount: "Existing Loan/EMI Amount",
  checking_account_balance: "Checking Account Balance",
  savings_account_balance: "Savings Account Balance",
  property_address: "Property Address",
  property_type: "Property Type",
  property_value: "Property Value",
  purchase_price: "Purchase Price",
  down_payment_amount: "Down Payment Amount",
  loan_term_years: "Loan Term (Years)",
  occupancy_type: "Occupancy Type",
}

export const HOME_LOAN_FIELD_KEYS = Object.keys(HOME_LOAN_FIELD_LABELS)

export const homeLoanDetailsSchema = z.object({
  employment_type: z.enum(EMPLOYMENT_TYPES, { message: "Select an employment type" }),
  employer_name: z.string().min(1, "Employer name is required"),
  job_title: z.string().min(1, "Job title is required"),
  employment_start_date: pastDate("Employment start date"),
  annual_income: requiredMoney("Annual income"),
  monthly_income: requiredMoney("Monthly income"),

  monthly_debt_payments: requiredMoney("Monthly debt payments"),
  existing_loan_emi_amount: requiredMoney("Existing loan/EMI amount"),
  checking_account_balance: requiredMoney("Checking account balance"),
  savings_account_balance: requiredMoney("Savings account balance"),

  property_address: z.string().min(1, "Property address is required"),
  property_type: z.enum(PROPERTY_TYPES, { message: "Select a property type" }),
  property_value: requiredMoney("Property value"),
  purchase_price: requiredMoney("Purchase price"),
  down_payment_amount: requiredMoney("Down payment amount"),
  loan_term_years: z.enum(LOAN_TERMS, { message: "Select a loan term" }),
  occupancy_type: z.enum(OCCUPANCY_TYPES, { message: "Select an occupancy type" }),
})

export type HomeLoanDetailsValues = z.infer<typeof homeLoanDetailsSchema>

export function HomeLoanDetailsStep({ form }: { form: UseFormReturn<any> }) {
  return (
    <div className="animate-step space-y-6">
      <DetailsStepHeader
        title="Home loan details"
        description="A few more details our partner banks require for a home loan."
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
          <MoneyField form={form} name="monthly_debt_payments" label="Monthly Debt Payments" placeholder="15000" />
          <MoneyField
            form={form}
            name="existing_loan_emi_amount"
            label="Existing Loan/EMI Amount"
            placeholder="10000"
          />
          <MoneyField
            form={form}
            name="checking_account_balance"
            label="Checking Account Balance"
            placeholder="250000"
          />
          <MoneyField
            form={form}
            name="savings_account_balance"
            label="Savings Account Balance"
            placeholder="500000"
          />
        </div>
      </div>

      <div className="space-y-3 border-t border-border pt-5">
        <SectionHeading>Property Information</SectionHeading>
        <div className="grid gap-4 sm:grid-cols-2">
          <TextAreaField
            form={form}
            name="property_address"
            label="Property Address"
            placeholder="Street, city, state, ZIP"
          />
          <SelectField
            form={form}
            name="property_type"
            label="Property Type"
            options={PROPERTY_TYPES}
            labels={PROPERTY_TYPE_LABELS}
          />
          <MoneyField form={form} name="property_value" label="Property Value" placeholder="6000000" />
          <MoneyField form={form} name="purchase_price" label="Purchase Price" placeholder="5800000" />
          <MoneyField form={form} name="down_payment_amount" label="Down Payment Amount" placeholder="1200000" />
          <SelectField
            form={form}
            name="loan_term_years"
            label="Loan Term (Years)"
            options={LOAN_TERMS}
            labels={Object.fromEntries(LOAN_TERMS.map((t) => [t, `${t} years`]))}
          />
          <SelectField
            form={form}
            name="occupancy_type"
            label="Occupancy Type"
            options={OCCUPANCY_TYPES}
            labels={OCCUPANCY_TYPE_LABELS}
          />
        </div>
      </div>
    </div>
  )
}
