import { Moon, Sun } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { ApiResponsePanel } from "@/components/shared/ApiResponsePanel"
import { PageHeader } from "@/components/shared/PageHeader"
import { useApiTester } from "@/hooks/useApiTester"
import { useAuth } from "@/contexts/AuthContext"
import { useTheme } from "@/contexts/ThemeContext"
import { API_BASE_URL, runApiCall } from "@/services/apiClient"

export function SettingsPage() {
  const { user, email, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const rootTester = useApiTester(() => runApiCall({ method: "GET", url: "/" }))

  return (
    <div className="space-y-6">
      <PageHeader title="Settings" description="Session details, API configuration, and appearance." />

      <Card>
        <CardHeader>
          <CardTitle>Session</CardTitle>
          <CardDescription>Your current authenticated identity.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Email</span>
            <span className="font-medium">{user?.email ?? email}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Role</span>
            <Badge variant="secondary" className="capitalize">
              {user?.role ?? "…"}
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">User ID</span>
            <span className="font-mono text-xs">{user?.id ?? "—"}</span>
          </div>
          <Separator />
          <Button variant="destructive" size="sm" onClick={logout}>
            Log out
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>API configuration</CardTitle>
          <CardDescription>Read from the <code>VITE_API_URL</code> environment variable.</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="font-mono text-xs text-muted-foreground">{API_BASE_URL}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
          <CardDescription>Toggle between light and dark themes.</CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="outline" onClick={toggleTheme}>
            {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
            Switch to {theme === "dark" ? "light" : "dark"} mode
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Health check</CardTitle>
          <CardDescription>GET / — confirms the backend is reachable.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Button onClick={() => rootTester.execute()} disabled={rootTester.isLoading}>
            Ping backend
          </Button>
          <ApiResponsePanel
            method="GET"
            path="/"
            isLoading={rootTester.isLoading}
            result={rootTester.result}
          />
        </CardContent>
      </Card>
    </div>
  )
}
