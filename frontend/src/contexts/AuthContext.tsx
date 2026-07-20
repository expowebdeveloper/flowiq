import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react"
import {
  clearStoredAuth,
  getStoredEmail,
  getStoredToken,
  registerUnauthorizedHandler,
  setStoredAuth,
} from "@/services/apiClient"
import { authService } from "@/services/authService"
import type { CurrentUser } from "@/types/api"

interface AuthContextValue {
  user: CurrentUser | null
  email: string | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (token: string, email: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => getStoredToken())
  const [email, setEmail] = useState<string | null>(() => getStoredEmail())
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const logout = useCallback(() => {
    clearStoredAuth()
    setToken(null)
    setEmail(null)
    setUser(null)
  }, [])

  const login = useCallback((newToken: string, newEmail: string) => {
    setStoredAuth(newToken, newEmail)
    setToken(newToken)
    setEmail(newEmail)
  }, [])

  useEffect(() => {
    registerUnauthorizedHandler(logout)
  }, [logout])

  useEffect(() => {
    if (!token) {
      setIsLoading(false)
      return
    }
    let cancelled = false
    setIsLoading(true)
    authService.me().then((result) => {
      if (cancelled) return
      if (result.ok && result.data) {
        setUser(result.data)
      } else {
        logout()
      }
      setIsLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [token, logout])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      email,
      token,
      isAuthenticated: Boolean(token),
      isLoading,
      login,
      logout,
    }),
    [user, email, token, isLoading, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}
