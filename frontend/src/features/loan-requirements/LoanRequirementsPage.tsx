import { useCallback, useEffect, useState } from "react"
import { PageHeader } from "@/components/shared/PageHeader"
import { banksService } from "@/services/banksService"
import type { LoanRequirement } from "@/types/api"
import { RequirementBoard } from "./RequirementBoard"

export function LoanRequirementsPage() {
  const [requirements, setRequirements] = useState<LoanRequirement[] | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchRequirements = useCallback(() => {
    setIsLoading(true)
    setError(null)
    banksService.listGlobalRequirements().then((result) => {
      if (result.ok && result.data) {
        setRequirements(result.data.commands)
      } else {
        setError(result.errorMessage ?? "Failed to load loan requirements")
      }
      setIsLoading(false)
    })
  }, [])

  useEffect(() => {
    fetchRequirements()
  }, [fetchRequirements])

  return (
    <div className="space-y-6">
      <PageHeader
        title="Loan Type Configuration"
        description="Define instructions the loan-processing agent should follow, scoped to a specific loan type or all loan types."
      />
      <RequirementBoard
        requirements={requirements}
        isLoading={isLoading}
        error={error}
        addButtonLabel="Add Requirement"
        emptyStateText="No loan requirements defined yet. Add one to give the agent extra instructions for a loan type."
        onCreate={(payload) => banksService.createGlobalRequirement(payload)}
        onUpdate={(id, payload) => banksService.updateRequirement(id, payload)}
        onDelete={(id) => banksService.deleteRequirement(id)}
        onChanged={fetchRequirements}
      />
    </div>
  )
}
