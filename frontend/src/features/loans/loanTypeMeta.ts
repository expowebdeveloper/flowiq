import { Car, GraduationCap, Home, User, Coins, type LucideIcon } from "lucide-react"
import { LOAN_TYPES, type LoanType } from "@/types/api"

interface LoanTypeMeta {
  label: string
  icon: LucideIcon
  description: string
}

export const LOAN_TYPE_META: Record<LoanType, LoanTypeMeta> = {
  home_loan: { label: "Home Loan", icon: Home, description: "Buy, build, or renovate a home" },
  education_loan: {
    label: "Education Loan",
    icon: GraduationCap,
    description: "Fund studies in India or abroad",
  },
  personal_loan: {
    label: "Personal Loan",
    icon: User,
    description: "Unsecured loan for personal needs",
  },
  car_loan: { label: "Car Loan", icon: Car, description: "Finance a new or used vehicle" },
  gold_loan: { label: "Gold Loan", icon: Coins, description: "Borrow against gold collateral" },
}

export function loanTypeLabel(type: string): string {
  return LOAN_TYPE_META[type as LoanType]?.label ?? type.replace(/_/g, " ")
}

export { LOAN_TYPES }
