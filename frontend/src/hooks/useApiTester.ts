import { useCallback, useState } from "react"
import type { ApiCallMeta } from "@/services/apiClient"

type ApiResult<T> = ApiCallMeta & { data: T | null; ok: boolean }

/**
 * Wraps any `runApiCall`-shaped service function with loading/result state
 * so tester forms can render request/response/status/timing uniformly.
 */
export function useApiTester<TArgs extends unknown[], TData>(
  fn: (...args: TArgs) => Promise<ApiResult<TData>>,
) {
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<ApiResult<TData> | null>(null)

  const execute = useCallback(
    async (...args: TArgs) => {
      setIsLoading(true)
      const res = await fn(...args)
      setResult(res)
      setIsLoading(false)
      return res
    },
    [fn],
  )

  const reset = useCallback(() => setResult(null), [])

  return { execute, isLoading, result, reset }
}
