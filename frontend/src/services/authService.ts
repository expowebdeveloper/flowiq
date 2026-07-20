import { API_BASE_URL, runApiCall } from "./apiClient"
import type { AuthStatusResponse, CurrentUser, LoginResponse } from "@/types/api"

export function buildGoogleLinkUrl(email?: string): string {
  const url = new URL("/auth/link", API_BASE_URL)
  if (email) url.searchParams.set("email", email)
  return url.toString()
}

export const authService = {
  me: () => runApiCall<CurrentUser>({ method: "GET", url: "/auth/me" }),

  status: (email: string) =>
    runApiCall<AuthStatusResponse>({
      method: "GET",
      url: "/auth/status",
      params: { email },
    }),

  login: (email: string, password: string) =>
    runApiCall<LoginResponse>({
      method: "POST",
      url: "/auth/login",
      data: { email, password },
    }),
}
