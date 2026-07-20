import { runApiCall } from "./apiClient"

export interface JsonVerifyResult {
  is_verified: boolean
  status: "verified" | "failed" | "unverified" | "error"
  message?: string
  errors: string[]
  warnings: string[]
}

export const jsonVerifyService = {
  verify: (formData: FormData) =>
    runApiCall<JsonVerifyResult>({
      method: "POST",
      url: "/json-verify",
      data: formData,
      headers: { "Content-Type": "multipart/form-data" },
    }),
}
