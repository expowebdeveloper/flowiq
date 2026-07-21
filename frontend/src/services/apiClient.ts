import axios, {
  AxiosError,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from "axios"

export const API_BASE_URL = import.meta.env.VITE_API_URL

export const TOKEN_STORAGE_KEY = "flowiq.auth.token"
export const EMAIL_STORAGE_KEY = "flowiq.auth.email"

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY)
}

export function getStoredEmail(): string | null {
  return localStorage.getItem(EMAIL_STORAGE_KEY)
}

export function setStoredAuth(token: string, email: string) {
  localStorage.setItem(TOKEN_STORAGE_KEY, token)
  localStorage.setItem(EMAIL_STORAGE_KEY, email)
}

export function clearStoredAuth() {
  localStorage.removeItem(TOKEN_STORAGE_KEY)
  localStorage.removeItem(EMAIL_STORAGE_KEY)
}

/**
 * The backend's OAuth callback redirects to `/?linked=1&email=...&token=...`
 * on the root path — not `/login` — so this must run before the router
 * decides whether the (still-unauthenticated) root should bounce to
 * `/login` and drop the query string. Call once, as early as possible
 * (module load in main.tsx), before anything reads stored auth state.
 */
export function captureOAuthRedirect() {
  const params = new URLSearchParams(window.location.search)
  const token = params.get("token")
  const email = params.get("email")
  if (params.get("linked") === "1" && token && email) {
    setStoredAuth(token, email)
    const url = new URL(window.location.href)
    url.searchParams.delete("linked")
    url.searchParams.delete("token")
    url.searchParams.delete("email")
    window.history.replaceState({}, "", url.pathname + url.search + url.hash)
  }
}

declare module "axios" {
  interface InternalAxiosRequestConfig {
    metadata?: { startTime: number }
  }
}

/**
 * Builds a ws(s):// URL for a given API path, preserving whatever path
 * prefix API_BASE_URL itself has (e.g. "/api" behind the nginx proxy) —
 * `new URL(path, API_BASE_URL)` would only work if API_BASE_URL ended in
 * a trailing slash, and plain string concatenation would drop the origin's
 * protocol swap, so this does both explicitly.
 */
export function buildWsUrl(path: string): URL {
  const wsUrl = new URL(API_BASE_URL, window.location.origin)
  wsUrl.protocol = wsUrl.protocol === "https:" ? "wss:" : "ws:"
  wsUrl.pathname = wsUrl.pathname.replace(/\/+$/, "") + path
  return wsUrl
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60_000,
})

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  config.metadata = { startTime: performance.now() }
  const token = getStoredToken()
  if (token) {
    config.headers.set("Authorization", `Bearer ${token}`)
  }
  return config
})

let onUnauthorized: (() => void) | null = null

export function registerUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler
}

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401 && onUnauthorized) {
      onUnauthorized()
    }
    return Promise.reject(error)
  },
)

export interface ApiCallMeta {
  status: number | null
  durationMs: number
  requestPayload?: unknown
  responseData?: unknown
  errorMessage?: string
}

/**
 * Runs an Axios request and always resolves (never throws) with full
 * request/response/timing metadata — used by the API tester forms so every
 * outcome (success or failure) can be rendered identically.
 */
export async function runApiCall<T = unknown>(
  config: AxiosRequestConfig,
): Promise<ApiCallMeta & { data: T | null; ok: boolean }> {
  const startTime = performance.now()
  try {
    const response = await apiClient.request<T>(config)
    return {
      ok: true,
      status: response.status,
      durationMs: performance.now() - startTime,
      requestPayload: config.data ?? config.params,
      responseData: response.data,
      data: response.data,
    }
  } catch (err) {
    const error = err as AxiosError
    const durationMs = performance.now() - startTime
    if (error.response) {
      return {
        ok: false,
        status: error.response.status,
        durationMs,
        requestPayload: config.data ?? config.params,
        responseData: error.response.data,
        errorMessage: extractErrorMessage(error.response.data),
        data: null,
      }
    }
    return {
      ok: false,
      status: null,
      durationMs,
      requestPayload: config.data ?? config.params,
      errorMessage: error.message || "Network error — is the backend running?",
      data: null,
    }
  }
}

export function extractErrorMessage(data: unknown): string {
  if (!data || typeof data !== "object") return "Request failed"
  const detail = (data as { detail?: unknown }).detail
  if (typeof detail === "string") return detail
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (typeof d === "object" && d && "msg" in d ? String(d.msg) : String(d)))
      .join("; ")
  }
  return "Request failed"
}
