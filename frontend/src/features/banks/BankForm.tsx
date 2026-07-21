import { useState } from "react"
import { Eye, EyeOff } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { BankPayload } from "@/services/banksService"

interface BankFormProps {
  value: BankPayload
  onChange: (value: BankPayload) => void
}

/**
 * Plain, presentational field set shared by the "Add Bank" page and the
 * Bank Detail page's inline edit mode — no Dialog, no submit button; the
 * parent owns the surrounding <form> and its own save/cancel actions.
 */
export function BankForm({ value, onChange }: BankFormProps) {
  const [showPortalPassword, setShowPortalPassword] = useState(false)

  function set<K extends keyof BankPayload>(key: K, val: BankPayload[K]) {
    onChange({ ...value, [key]: val })
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <div className="space-y-1.5">
        <Label htmlFor="bank-name">Bank Name</Label>
        <Input
          id="bank-name"
          value={value.name}
          onChange={(e) => set("name", e.target.value)}
          placeholder="e.g. State Bank of India"
          required
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="bank-status">Status</Label>
        <Select value={value.status} onValueChange={(val) => set("status", val)}>
          <SelectTrigger id="bank-status">
            <SelectValue placeholder="Select status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="inactive">Inactive</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="bank-website">Website URL (optional)</Label>
        <Input
          id="bank-website"
          type="url"
          value={value.website ?? ""}
          onChange={(e) => set("website", e.target.value)}
          placeholder="https://..."
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="bank-logo">Logo Image URL (optional)</Label>
        <Input
          id="bank-logo"
          value={value.logo ?? ""}
          onChange={(e) => set("logo", e.target.value)}
          placeholder="https://.../logo.png"
        />
      </div>

      <div className="space-y-1.5 sm:col-span-2">
        <Label htmlFor="bank-contact-email">Contact Email (optional)</Label>
        <Input
          id="bank-contact-email"
          type="email"
          value={value.contact_email ?? ""}
          onChange={(e) => set("contact_email", e.target.value)}
          placeholder="loans@bank.com"
        />
        <p className="text-xs text-muted-foreground">
          Must be unique — no two banks can share the same contact email.
        </p>
      </div>

      <div className="space-y-1.5 sm:col-span-2">
        <div className="border-t border-border pt-4">
          <Label className="text-sm font-medium">Bank Portal Login (optional)</Label>
          <p className="text-xs text-muted-foreground">
            For a future automation where the agent signs in to the bank's own portal directly. Stored
            as plain text so it can be reused for that login — do not enter anything more sensitive
            than a dedicated automation account.
          </p>
        </div>
      </div>

      <div className="space-y-1.5 sm:col-span-2">
        <Label htmlFor="bank-portal-url">Portal URL</Label>
        <Input
          id="bank-portal-url"
          type="url"
          value={value.portal_url ?? ""}
          onChange={(e) => set("portal_url", e.target.value)}
          placeholder="https://portal.bank.com/login"
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="bank-portal-username">Portal Username</Label>
        <Input
          id="bank-portal-username"
          value={value.portal_username ?? ""}
          onChange={(e) => set("portal_username", e.target.value)}
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="bank-portal-password">Portal Password</Label>
        <div className="relative">
          <Input
            id="bank-portal-password"
            type={showPortalPassword ? "text" : "password"}
            value={value.portal_password ?? ""}
            onChange={(e) => set("portal_password", e.target.value)}
            className="pr-10"
          />
          <button
            type="button"
            onClick={() => setShowPortalPassword((v) => !v)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            aria-label={showPortalPassword ? "Hide password" : "Show password"}
          >
            {showPortalPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
          </button>
        </div>
      </div>
    </div>
  )
}
