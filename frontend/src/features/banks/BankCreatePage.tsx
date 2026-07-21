import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { ArrowLeft, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { banksService, type BankPayload } from "@/services/banksService"
import { BankForm } from "./BankForm"

const emptyForm: BankPayload = {
  name: "",
  website: "",
  logo: "",
  status: "active",
  contact_email: "",
  portal_url: "",
  portal_username: "",
  portal_password: "",
}

export function BankCreatePage() {
  const navigate = useNavigate()
  const [form, setForm] = useState<BankPayload>(emptyForm)
  const [isSaving, setIsSaving] = useState(false)

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    if (!form.name.trim()) return

    setIsSaving(true)
    const result = await banksService.createBank(form)
    setIsSaving(false)

    if (result.ok && result.data?.bank_id) {
      navigate(`/banks/${result.data.bank_id}`)
    } else {
      alert(result.errorMessage ?? "Error creating bank")
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => navigate("/banks")} aria-label="Back to banks">
          <ArrowLeft className="size-4" />
        </Button>
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Add Bank</h2>
          <p className="text-sm text-muted-foreground">
            Create a bank, then configure its supported loan types and requirements on its detail page.
          </p>
        </div>
      </div>

      <Card>
        <CardContent className="pt-6">
          <form onSubmit={handleSave} className="space-y-6">
            <BankForm value={form} onChange={setForm} />
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => navigate("/banks")}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSaving}>
                {isSaving && <Loader2 className="size-4 animate-spin" />}
                Create Bank
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
