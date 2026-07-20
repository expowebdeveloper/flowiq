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
  requiredMoney,
} from "./LoanFieldPrimitives"

const RELATIONSHIPS = ["parent", "spouse", "sibling", "guardian", "other"] as const
const RELATIONSHIP_LABELS: Record<(typeof RELATIONSHIPS)[number], string> = {
  parent: "Parent",
  spouse: "Spouse",
  sibling: "Sibling",
  guardian: "Guardian",
  other: "Other",
}

const LOAN_TERMS_YEARS = ["3", "5", "7", "10", "15"] as const

/** Field key -> human label for the lead detail page (see leads/LeadsPage.tsx). */
export const EDUCATION_LOAN_FIELD_LABELS: Record<string, string> = {
  current_address: "Current Address",
  university_name: "University/College Name",
  course_name: "Course/Degree",
  course_duration_years: "Course Duration (Years)",
  tuition_fee: "Tuition Fee",
  expected_graduation_date: "Expected Graduation Date",
  co_applicant_name: "Co-Applicant Name",
  co_applicant_relationship: "Relationship",
  co_applicant_employment_type: "Co-Applicant Employment Type",
  co_applicant_employer_name: "Co-Applicant Employer Name",
  co_applicant_annual_income: "Co-Applicant Annual Income",
  loan_term_years: "Loan Term (Years)",
  existing_loan_emi_amount: "Existing Monthly Loan/EMI Amount",
}

export const EDUCATION_LOAN_FIELD_KEYS = Object.keys(EDUCATION_LOAN_FIELD_LABELS)

export const educationLoanDetailsSchema = z.object({
  current_address: z.string().min(1, "Current address is required"),

  university_name: z.string().min(1, "University/college name is required"),
  course_name: z.string().min(1, "Course/degree is required"),
  course_duration_years: z
    .string()
    .min(1, "Course duration is required")
    .refine((v) => !isNaN(Number(v)) && Number(v) > 0, { message: "Enter a valid number of years" }),
  tuition_fee: requiredMoney("Tuition fee"),
  expected_graduation_date: z
    .string()
    .min(1, "Expected graduation date is required")
    .refine((v) => !isNaN(new Date(v).getTime()), { message: "Enter a valid date" }),

  co_applicant_name: z.string().min(1, "Co-applicant name is required"),
  co_applicant_relationship: z.enum(RELATIONSHIPS, { message: "Select a relationship" }),
  co_applicant_employment_type: z.enum(EMPLOYMENT_TYPES, { message: "Select an employment type" }),
  co_applicant_employer_name: z.string().min(1, "Co-applicant employer name is required"),
  co_applicant_annual_income: requiredMoney("Co-applicant annual income"),

  loan_term_years: z.enum(LOAN_TERMS_YEARS, { message: "Select a loan term" }),
  existing_loan_emi_amount: requiredMoney("Existing loan/EMI amount"),
})

export type EducationLoanDetailsValues = z.infer<typeof educationLoanDetailsSchema>

export function EducationLoanDetailsStep({ form }: { form: UseFormReturn<any> }) {
  return (
    <div className="animate-step space-y-6">
      <DetailsStepHeader
        title="Education loan details"
        description="A few more details our partner banks require for an education loan."
      />

      <div className="space-y-3">
        <SectionHeading>Student Information</SectionHeading>
        <div className="grid gap-4 sm:grid-cols-2">
          <TextAreaField
            form={form}
            name="current_address"
            label="Current Address"
            placeholder="Street, city, state, ZIP"
          />
        </div>
      </div>

      <div className="space-y-3 border-t border-border pt-5">
        <SectionHeading>Education Information</SectionHeading>
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField
            form={form}
            name="university_name"
            label="University/College Name"
            placeholder="Indian Institute of Technology"
          />
          <TextField form={form} name="course_name" label="Course/Degree" placeholder="B.Tech Computer Science" />
          <TextField
            form={form}
            name="course_duration_years"
            label="Course Duration (Years)"
            type="number"
            placeholder="4"
          />
          <MoneyField form={form} name="tuition_fee" label="Tuition Fee" placeholder="800000" />
          <TextField
            form={form}
            name="expected_graduation_date"
            label="Expected Graduation Date"
            type="date"
          />
        </div>
      </div>

      <div className="space-y-3 border-t border-border pt-5">
        <SectionHeading>Co-Applicant Information</SectionHeading>
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField form={form} name="co_applicant_name" label="Co-Applicant Name" placeholder="Jane Doe" />
          <SelectField
            form={form}
            name="co_applicant_relationship"
            label="Relationship"
            options={RELATIONSHIPS}
            labels={RELATIONSHIP_LABELS}
          />
          <SelectField
            form={form}
            name="co_applicant_employment_type"
            label="Employment Type"
            options={EMPLOYMENT_TYPES}
            labels={EMPLOYMENT_TYPE_LABELS}
          />
          <TextField
            form={form}
            name="co_applicant_employer_name"
            label="Employer Name"
            placeholder="Acme Inc."
          />
          <MoneyField
            form={form}
            name="co_applicant_annual_income"
            label="Annual Income"
            placeholder="1500000"
          />
        </div>
      </div>

      <div className="space-y-3 border-t border-border pt-5">
        <SectionHeading>Loan Information</SectionHeading>
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField
            form={form}
            name="loan_term_years"
            label="Loan Term (Years)"
            options={LOAN_TERMS_YEARS}
            labels={Object.fromEntries(LOAN_TERMS_YEARS.map((t) => [t, `${t} years`]))}
          />
          <MoneyField
            form={form}
            name="existing_loan_emi_amount"
            label="Existing Monthly Loan/EMI Amount"
            placeholder="5000"
          />
        </div>
      </div>
    </div>
  )
}
