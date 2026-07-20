import { useEffect, useState } from "react"
import { Loader2, Paperclip } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useAuth } from "@/contexts/AuthContext"
import { banksService } from "@/services/banksService"
import type { LoanApplication } from "@/types/api"

const STATUS_VARIANT: Record<string, "success" | "warning" | "destructive" | "secondary"> = {
  submitted: "secondary",
  under_review: "warning",
  approved: "success",
  rejected: "destructive",
}

export function BankDashboardPage() {
  const { user } = useAuth()
  const [applications, setApplications] = useState<LoanApplication[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    banksService.listApplicationsForBank().then((result) => {
      if (result.ok && result.data) {
        setApplications(result.data.applications)
      } else {
        setErrorMessage(result.errorMessage ?? "Failed to load applications")
      }
      setIsLoading(false)
    })
  }, [])

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight">
          {user?.bank_name ?? "Bank"} — Loan Applications
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Applicants who submitted a loan application to your bank.
        </p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="size-5 animate-spin text-muted-foreground" />
        </div>
      ) : errorMessage ? (
        <p className="text-sm text-destructive">{errorMessage}</p>
      ) : applications.length === 0 ? (
        <p className="text-sm text-muted-foreground">No applications yet.</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {applications.map((app) => (
            <Card key={app.id}>
              <CardHeader className="flex-row items-start justify-between space-y-0">
                <div>
                  <CardTitle className="text-base">{app.applicant_name}</CardTitle>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {app.loan_type.replace("_", " ")} &middot;{" "}
                    {new Date(app.created_at).toLocaleDateString()}
                  </p>
                </div>
                <Badge variant={STATUS_VARIANT[app.status] ?? "secondary"}>
                  {app.status.replace("_", " ")}
                </Badge>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p>
                  <span className="text-muted-foreground">Phone:</span> {app.applicant_phone}
                </p>
                {app.applicant_email && (
                  <p>
                    <span className="text-muted-foreground">Email:</span> {app.applicant_email}
                  </p>
                )}
                {app.notes && (
                  <p className="text-muted-foreground">{app.notes}</p>
                )}
                {app.documents.length > 0 && (
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <Paperclip className="size-3.5" />
                    {app.documents.length} document{app.documents.length === 1 ? "" : "s"}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
