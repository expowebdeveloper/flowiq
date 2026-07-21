import { z } from "zod"
import type { UseFormReturn } from "react-hook-form"

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

/**
 * Shared field renderers + Zod helpers for every per-loan-type details form
 * (see *DetailsStep.tsx siblings in this folder). Centralized here so each
 * loan type's form composes the same building blocks instead of
 * reimplementing text/money/date/select inputs five times over.
 */

/** Matches the larger control sizing used on the base LoanApplyPage.tsx form. */
const FIELD_SIZE = "h-14 px-4 text-lg"
const TEXTAREA_SIZE = "min-h-28 px-4 py-3 text-lg"

export const SSN_RE = /^\d{3}-?\d{2}-?\d{4}$/
export const PHONE_RE = /^\d{10}$/

export const EMPLOYMENT_TYPES = ["salaried", "self_employed", "business_owner", "retired", "unemployed"] as const
export const EMPLOYMENT_TYPE_LABELS: Record<(typeof EMPLOYMENT_TYPES)[number], string> = {
  salaried: "Salaried",
  self_employed: "Self-Employed",
  business_owner: "Business Owner",
  retired: "Retired",
  unemployed: "Unemployed",
}

export function requiredMoney(label: string) {
  return z
    .string()
    .min(1, `${label} is required`)
    .refine((v) => !isNaN(Number(v)) && Number(v) >= 0, { message: `Enter a valid ${label.toLowerCase()}` })
}

export function pastDate(label: string) {
  return z
    .string()
    .min(1, `${label} is required`)
    .refine((v) => !isNaN(new Date(v).getTime()) && new Date(v) <= new Date(), {
      message: `${label} cannot be in the future`,
    })
}

export function futureOrPastDate(label: string) {
  return z
    .string()
    .min(1, `${label} is required`)
    .refine((v) => !isNaN(new Date(v).getTime()), { message: `Enter a valid date` })
}

interface FieldProps {
  form: UseFormReturn<any>
  name: string
  label: string
}

export function FieldErrorText({ form, name }: { form: UseFormReturn<any>; name: string }) {
  const message = (form.formState.errors as any)?.extra_loan_details?.[name]?.message
  if (!message) return null
  return <p className="text-xs text-destructive">{message}</p>
}

export function TextField({
  form,
  name,
  label,
  placeholder,
  type = "text",
}: FieldProps & { placeholder?: string; type?: string }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Input
        className={FIELD_SIZE}
        type={type}
        placeholder={placeholder}
        {...form.register(`extra_loan_details.${name}`)}
      />
      <FieldErrorText form={form} name={name} />
    </div>
  )
}

export function MoneyField({ form, name, label, placeholder }: FieldProps & { placeholder?: string }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <div className="relative">
        <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
        <Input
          type="number"
          inputMode="decimal"
          min={0}
          placeholder={placeholder}
          className={`${FIELD_SIZE} pl-8`}
          {...form.register(`extra_loan_details.${name}`)}
        />
      </div>
      <FieldErrorText form={form} name={name} />
    </div>
  )
}

export function TextAreaField({ form, name, label, placeholder }: FieldProps & { placeholder?: string }) {
  return (
    <div className="space-y-1.5 sm:col-span-2">
      <Label>{label}</Label>
      <Textarea
        className={TEXTAREA_SIZE}
        placeholder={placeholder}
        {...form.register(`extra_loan_details.${name}`)}
      />
      <FieldErrorText form={form} name={name} />
    </div>
  )
}

export function SelectField({
  form,
  name,
  label,
  options,
  labels,
}: FieldProps & { options: readonly string[]; labels: Record<string, string> }) {
  const value = form.watch(`extra_loan_details.${name}`)
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Select
        value={value}
        onValueChange={(v) => form.setValue(`extra_loan_details.${name}`, v, { shouldValidate: true })}
      >
        <SelectTrigger className={FIELD_SIZE}>
          <SelectValue placeholder="Select" />
        </SelectTrigger>
        <SelectContent>
          {options.map((opt) => (
            <SelectItem key={opt} value={opt}>
              {labels[opt]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <FieldErrorText form={form} name={name} />
    </div>
  )
}

export function SectionHeading({ children }: { children: string }) {
  return <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{children}</h3>
}

export function DetailsStepHeader({ title, description }: { title: string; description: string }) {
  return (
    <div>
      <h2 className="text-lg font-semibold" style={{ fontFamily: "var(--font-display)" }}>
        {title}
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">{description}</p>
    </div>
  )
}
