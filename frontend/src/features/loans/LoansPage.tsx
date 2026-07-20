import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { PageHeader } from "@/components/shared/PageHeader"
import { CategoryGrid } from "./CategoryGrid"
import { BankList } from "./BankList"
import type { LoanType } from "@/types/api"

type Step = { name: "categories" } | { name: "banks"; loanType: LoanType }

export function LoansPage() {
  const [step, setStep] = useState<Step>({ name: "categories" })
  const navigate = useNavigate()

  return (
    <div className="space-y-6">
      <PageHeader
        title="Loans"
        description="Browse loan categories, compare bank rates, and submit an application."
      />

      {step.name === "categories" && (
        <CategoryGrid onSelect={(loanType) => setStep({ name: "banks", loanType })} />
      )}

      {step.name === "banks" && (
        <BankList
          loanType={step.loanType}
          onBack={() => setStep({ name: "categories" })}
          onApply={(rate) => navigate(`/loan-apply?loan_type=${encodeURIComponent(rate.loan_type)}`)}
        />
      )}
    </div>
  )
}
