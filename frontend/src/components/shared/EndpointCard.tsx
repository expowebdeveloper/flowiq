import type { ReactNode } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

interface EndpointCardProps {
  method: "GET" | "POST" | "PUT" | "DELETE"
  path: string
  title: string
  description?: string
  children: ReactNode
}

const methodColors: Record<EndpointCardProps["method"], string> = {
  GET: "bg-success/15 text-success border-success/30",
  POST: "bg-primary/15 text-primary border-primary/30",
  PUT: "bg-warning/15 text-warning border-warning/30",
  DELETE: "bg-destructive/15 text-destructive border-destructive/30",
}

export function EndpointCard({ method, path, title, description, children }: EndpointCardProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <Badge className={methodColors[method]} variant="outline">
            {method}
          </Badge>
          <code className="text-xs text-muted-foreground">{path}</code>
        </div>
        <CardTitle className="pt-1">{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent className="space-y-4">{children}</CardContent>
    </Card>
  )
}
