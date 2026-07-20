import { AlertCircle, Clock, Loader2 } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { cn, formatMs } from "@/lib/utils"
import type { ApiCallMeta } from "@/services/apiClient"

interface ApiResponsePanelProps {
  method: string
  path: string
  isLoading: boolean
  result: (ApiCallMeta & { ok: boolean }) | null
}

function statusVariant(status: number | null): "success" | "destructive" | "warning" | "secondary" {
  if (status === null) return "secondary"
  if (status >= 200 && status < 300) return "success"
  if (status >= 400) return "destructive"
  return "warning"
}

export function ApiResponsePanel({ method, path, isLoading, result }: ApiResponsePanelProps) {
  return (
    <div className="rounded-lg border border-border bg-muted/30">
      <div className="flex flex-wrap items-center gap-2 border-b border-border px-4 py-2.5">
        <Badge variant="outline" className="font-mono">
          {method}
        </Badge>
        <code className="text-xs text-muted-foreground">{path}</code>
        <div className="ml-auto flex items-center gap-2">
          {isLoading && (
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Loader2 className="size-3 animate-spin" /> Running…
            </span>
          )}
          {!isLoading && result && (
            <>
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                <Clock className="size-3" /> {formatMs(result.durationMs)}
              </span>
              <Badge variant={statusVariant(result.status)}>
                {result.status ?? "NETWORK ERROR"}
              </Badge>
            </>
          )}
        </div>
      </div>

      {!isLoading && !result && (
        <div className="px-4 py-6 text-center text-sm text-muted-foreground">
          Submit the form to see the request and response here.
        </div>
      )}

      {!isLoading && result && (
        <div className="grid gap-3 p-4 md:grid-cols-2">
          <div>
            <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Request payload
            </p>
            <pre className="scrollbar-thin max-h-72 overflow-auto rounded-md bg-background p-3 text-xs">
              {result.requestPayload
                ? JSON.stringify(result.requestPayload, null, 2)
                : "(none)"}
            </pre>
          </div>
          <div>
            <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Response
            </p>
            <pre
              className={cn(
                "scrollbar-thin max-h-72 overflow-auto rounded-md bg-background p-3 text-xs",
                !result.ok && "text-destructive",
              )}
            >
              {JSON.stringify(result.responseData ?? { error: result.errorMessage }, null, 2)}
            </pre>
          </div>

          {!result.ok && result.errorMessage && (
            <div className="flex items-start gap-2 rounded-md bg-destructive/10 p-3 text-sm text-destructive md:col-span-2">
              <AlertCircle className="mt-0.5 size-4 shrink-0" />
              <span>{result.errorMessage}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
