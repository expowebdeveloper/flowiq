import { Link } from "react-router-dom"
import { ArrowUpRight, Server } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useAuth } from "@/contexts/AuthContext"
import { navItems } from "@/config/navigation"
import { API_BASE_URL } from "@/services/apiClient"
import { PipelineByStage } from "@/features/dashboard/PipelineByStage"

export function DashboardPage() {
  const { user, email } = useAuth()

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">
          Welcome back{user?.email ? `, ${user.email}` : ""}
        </h2>
        <p className="text-sm text-muted-foreground">
          Signed in as <span className="font-medium text-foreground">{email}</span>
          {user?.role && (
            <>
              {" "}
              · role <Badge variant="secondary" className="ml-1 align-middle capitalize">{user.role}</Badge>
            </>
          )}
        </p>
      </div>

      <PipelineByStage />

      <Card>
        <CardHeader className="flex-row items-center gap-3 space-y-0">
          <div className="flex size-9 items-center justify-center rounded-md bg-accent text-accent-foreground">
            <Server className="size-4" />
          </div>
          <div>
            <CardTitle>API target</CardTitle>
            <CardDescription className="font-mono text-xs">{API_BASE_URL}</CardDescription>
          </div>
        </CardHeader>
      </Card>

      <div>
        <h3 className="mb-3 text-sm font-medium text-muted-foreground">Modules</h3>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {navItems
            .filter((item) => item.path !== "/")
            .map((item) => (
              <Link key={item.path} to={item.path}>
                <Card className="group h-full transition-colors hover:border-primary/50 hover:bg-accent/40">
                  <CardHeader className="flex-row items-start justify-between space-y-0">
                    <div className="flex items-center gap-3">
                      <div className="flex size-9 items-center justify-center rounded-md bg-muted text-foreground">
                        <item.icon className="size-4" />
                      </div>
                      <div>
                        <CardTitle>{item.label}</CardTitle>
                        <CardDescription>{item.description}</CardDescription>
                      </div>
                    </div>
                    <ArrowUpRight className="size-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                  </CardHeader>
                </Card>
              </Link>
            ))}
        </div>
      </div>
    </div>
  )
}
