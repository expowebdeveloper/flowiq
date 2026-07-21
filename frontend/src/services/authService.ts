import { API_BASE_URL, runApiCall } from "./apiClient"
import type { AuthStatusResponse, CurrentUser, LoginResponse } from "@/types/api"

export function buildGoogleLinkUrl(email?: string): string {
  // API_BASE_URL carries a path prefix (e.g. "/api" behind the nginx proxy) —
  // new URL("/auth/link", API_BASE_URL) would replace that prefix instead of
  // appending to it, since a leading-slash path is resolved as absolute
  // against the origin. See buildWsUrl in apiClient.ts for the same gotcha.
  const url = new URL(API_BASE_URL, window.location.origin)
  url.pathname = url.pathname.replace(/\/+$/, "") + "/auth/link"
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
