import { runApiCall } from "./apiClient"
import type { KycApplicationDetail, KycSubmitResponse } from "@/types/api"

export const kycService = {
  getApplication: (token: string) =>
    runApiCall<KycApplicationDetail>({ method: "GET", url: `/kyc/${encodeURIComponent(token)}` }),

  submitKyc: (token: string, formData: FormData) =>
    runApiCall<KycSubmitResponse>({
      method: "POST",
      url: `/kyc/${encodeURIComponent(token)}`,
      data: formData,
      headers: { "Content-Type": "multipart/form-data" },
    }),
}
