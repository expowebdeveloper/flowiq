import { useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { AlertTriangle, CheckCircle2, Loader2 } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { kycService } from "@/services/kycService"
import { loanTypeLabel } from "@/features/loans/loanTypeMeta"
import type { KycApplicationDetail } from "@/types/api"
import { KycForm } from "./KycForm"

type State =
  | { name: "loading" }
  | { name: "error"; message: string }
  | { name: "form"; detail: KycApplicationDetail }
  | { name: "submitted"; bankNotified: boolean; banksNotifiedCount: number; warning: string | null }

export function KycFormPage() {
  const { token } = useParams<{ token: string }>()
  const [state, setState] = useState<State>({ name: "loading" })

  useEffect(() => {
    if (!token) {
      setState({ name: "error", message: "Missing KYC link token." })
      return
    }
    kycService.getApplication(token).then((result) => {
      if (result.ok && result.data) {
        setState({ name: "form", detail: result.data })
      } else {
        setState({
          name: "error",
          message: result.errorMessage ?? "This KYC link is invalid or has already been used.",
        })
      }
    })
  }, [token])

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 p-4">
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <CardTitle>Complete your KYC</CardTitle>
          {state.name === "form" && (
            <CardDescription>
              {state.detail.bank_name} · {loanTypeLabel(state.detail.loan_type)}
            </CardDescription>
          )}
          {state.name !== "form" && (
            <CardDescription>Verify your details to finish your loan application.</CardDescription>
          )}
        </CardHeader>
        <CardContent>
          {state.name === "loading" && (
            <div className="flex flex-col items-center gap-3 py-10 text-muted-foreground">
              <Loader2 className="size-6 animate-spin" />
              <p className="text-sm">Loading your application…</p>
            </div>
          )}

          {state.name === "error" && (
            <div className="flex flex-col items-center gap-3 py-10 text-center">
              <div className="flex size-14 items-center justify-center rounded-full bg-destructive/15 text-destructive">
                <AlertTriangle className="size-7" />
              </div>
              <div>
                <h3 className="text-lg font-semibold">Link unavailable</h3>
                <p className="mt-1 text-sm text-muted-foreground">{state.message}</p>
              </div>
            </div>
          )}

          {state.name === "form" && (
            <KycForm
              token={token!}
              detail={state.detail}
              onSubmitted={(bankNotified, banksNotifiedCount, warning) =>
                setState({ name: "submitted", bankNotified, banksNotifiedCount, warning })
              }
            />
          )}

          {state.name === "submitted" && (
            <div className="flex flex-col items-center gap-3 py-10 text-center">
              <div className="flex size-14 items-center justify-center rounded-full bg-success/15 text-success">
                <CheckCircle2 className="size-7" />
              </div>
              <div>
                <h3 className="text-lg font-semibold">KYC submitted</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  {state.bankNotified
                    ? `Your details have been sent to ${state.banksNotifiedCount} bank${state.banksNotifiedCount === 1 ? "" : "s"}. They'll be in touch shortly.`
                    : "Your details have been saved. The banks will be notified shortly."}
                </p>
                {state.warning && (
                  <p className="mt-2 text-xs text-muted-foreground">{state.warning}</p>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
