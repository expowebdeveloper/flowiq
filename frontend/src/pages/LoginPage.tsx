import { useEffect, useState } from "react"
import { Navigate, useNavigate, useSearchParams } from "react-router-dom"
import { Loader2, LogIn, ShieldCheck, Zap } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { useAuth } from "@/contexts/AuthContext"
import { authService, buildGoogleLinkUrl } from "@/services/authService"

export function LoginPage() {
  const { isAuthenticated, login } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const [isRedirecting, setIsRedirecting] = useState(false)

  const [bankEmail, setBankEmail] = useState("")
  const [bankPassword, setBankPassword] = useState("")
  const [isLoggingIn, setIsLoggingIn] = useState(false)
  const [loginError, setLoginError] = useState<string | null>(null)

  useEffect(() => {
    const token = searchParams.get("token")
    const linkedEmail = searchParams.get("email")
    if (token && linkedEmail) {
      login(token, linkedEmail)
      setSearchParams({}, { replace: true })
      navigate("/", { replace: true })
    }
  }, [searchParams, login, navigate, setSearchParams])

  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }

  function handleGoogleLogin() {
    setIsRedirecting(true)
    window.location.href = buildGoogleLinkUrl()
  }

  async function handleBankLogin(event: React.FormEvent) {
    event.preventDefault()
    setLoginError(null)
    setIsLoggingIn(true)
    const result = await authService.login(bankEmail, bankPassword)
    setIsLoggingIn(false)
    if (result.ok && result.data) {
      login(result.data.token, result.data.email)
      navigate("/", { replace: true })
    } else {
      setLoginError(result.errorMessage ?? "Invalid email or password")
    }
  }

  return (
    <div className="flex min-h-svh items-center justify-center bg-gradient-to-b from-background to-muted/40 p-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-3 flex size-11 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
            <Zap className="size-6" />
          </div>
          <h1 className="text-xl font-semibold tracking-tight">FlowIQ</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Sign in to view mail, manage loans, or monitor applications
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Sign in</CardTitle>
            <CardDescription>
              Brokers sign in with Google. Banks sign in with email and password.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button className="w-full" disabled={isRedirecting} onClick={handleGoogleLogin}>
              {isRedirecting ? (
                <>
                  <Loader2 className="size-4 animate-spin" /> Redirecting to Google…
                </>
              ) : (
                <>
                  <ShieldCheck className="size-4" /> Continue with Google
                </>
              )}
            </Button>

            <div className="my-5 flex items-center gap-3">
              <Separator className="flex-1" />
              <span className="text-xs text-muted-foreground">or bank login</span>
              <Separator className="flex-1" />
            </div>

            <form className="space-y-3" onSubmit={handleBankLogin}>
              <div className="space-y-1.5">
                <Label htmlFor="bank-email">Email</Label>
                <Input
                  id="bank-email"
                  type="email"
                  autoComplete="username"
                  value={bankEmail}
                  onChange={(e) => setBankEmail(e.target.value)}
                  placeholder="hdfc@flowiq.bank"
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="bank-password">Password</Label>
                <Input
                  id="bank-password"
                  type="password"
                  autoComplete="current-password"
                  value={bankPassword}
                  onChange={(e) => setBankPassword(e.target.value)}
                  required
                />
              </div>

              {loginError && <p className="text-sm text-destructive">{loginError}</p>}

              <Button
                type="submit"
                variant="secondary"
                className="w-full"
                disabled={isLoggingIn}
              >
                {isLoggingIn ? (
                  <>
                    <Loader2 className="size-4 animate-spin" /> Signing in…
                  </>
                ) : (
                  <>
                    <LogIn className="size-4" /> Sign in
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
