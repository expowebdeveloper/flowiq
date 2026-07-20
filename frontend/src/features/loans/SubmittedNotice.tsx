import { Clock3, PlusCircle } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

interface SubmittedNoticeProps {
  applicationId: string
  bankName: string
  onDone: () => void
}

export function SubmittedNotice({ applicationId, bankName, onDone }: SubmittedNoticeProps) {
  return (
    <Card className="mx-auto max-w-md">
      <CardContent className="flex flex-col items-center gap-4 p-8 text-center">
        <div className="flex size-14 items-center justify-center rounded-full bg-warning/15 text-warning">
          <Clock3 className="size-7" />
        </div>
        <div>
          <h3 className="text-lg font-semibold">Your request is being processed</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Your loan application to <span className="font-medium text-foreground">{bankName}</span> has
            been submitted and is now under review.
          </p>
        </div>
        {applicationId && (
          <Badge variant="secondary" className="font-mono text-xs">
            Application ID: {applicationId}
          </Badge>
        )}
        <Button onClick={onDone} className="mt-2">
          <PlusCircle className="size-4" /> Apply for another loan
        </Button>
      </CardContent>
    </Card>
  )
}
