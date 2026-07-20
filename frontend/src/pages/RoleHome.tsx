import { Loader2 } from "lucide-react"
import { AppLayout } from "@/components/layout/AppLayout"
import { BankDashboardPage } from "@/features/bank-dashboard/BankDashboardPage"
import { LoanApplyPage } from "@/features/loan-apply/LoanApplyPage"
import { useAuth } from "@/contexts/AuthContext"
import { DashboardPage } from "./DashboardPage"

/**
 * "/" is the public landing page: signed-out visitors get the loan apply
 * form, signed-in users get their role dashboard (banks get their activity
 * dashboard, everyone else gets the broker dashboard) inside the app shell.
 */
export function RoleHome() {
  const { user, isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex h-svh items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <LoanApplyPage />
  }

  return (
    <AppLayout>
      {user?.role === "bank" ? <BankDashboardPage /> : <DashboardPage />}
    </AppLayout>
  )
}
