import { ChevronRight } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { LOAN_TYPES } from "@/types/api"
import { LOAN_TYPE_META } from "./loanTypeMeta"
import type { LoanType } from "@/types/api"

interface CategoryGridProps {
  onSelect: (loanType: LoanType) => void
}

export function CategoryGrid({ onSelect }: CategoryGridProps) {
  return (
    <div>
      <h3 className="mb-3 text-sm font-medium text-muted-foreground">Choose a loan category</h3>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {LOAN_TYPES.map((type) => {
          const meta = LOAN_TYPE_META[type]
          return (
            <Card
              key={type}
              role="button"
              tabIndex={0}
              onClick={() => onSelect(type)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") onSelect(type)
              }}
              className="group cursor-pointer transition-colors hover:border-primary/50 hover:bg-accent/40"
            >
              <CardContent className="flex items-center gap-4 p-5">
                <div className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <meta.icon className="size-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-medium">{meta.label}</p>
                  <p className="truncate text-xs text-muted-foreground">{meta.description}</p>
                </div>
                <ChevronRight className="size-4 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
