import type { LucideIcon } from "lucide-react"
import {
  Activity,
  Bell,
  LayoutDashboard,
  PiggyBank,
  Settings,
  Building2,
  ClipboardCheck,
  UserPlus,
  Users,
} from "lucide-react"

export interface NavItem {
  label: string
  path: string
  icon: LucideIcon
  description: string
  /** Omit to show for every role; set true to hide from bank logins (those routes 403 for banks server-side). */
  brokerOnly?: boolean
  /** Set true to show only for bank logins (the inverse of brokerOnly — for bank-specific features like notifications). */
  bankOnly?: boolean
}

export const navItems: NavItem[] = [
  { label: "Dashboard", path: "/", icon: LayoutDashboard, description: "Overview" },
  { label: "Customer", path: "/notifications", icon: Bell, description: "New leads for your bank", bankOnly: true },
  { label: "Leads", path: "/leads", icon: Users, description: "Applicant submissions & documents", brokerOnly: true },
  { label: "AI Activity", path: "/ai-activity", icon: Activity, description: "Live AI background processing", brokerOnly: true },
  { label: "Loans", path: "/loans", icon: PiggyBank, description: "Browse banks & apply", brokerOnly: true },
  { label: "Banks", path: "/banks", icon: Building2, description: "Manage banks & policies", brokerOnly: true },
  { label: "Verify JSON", path: "/verify-json", icon: ClipboardCheck, description: "Validate application JSON", brokerOnly: true },
  { label: "Loan Apply", path: "/loan-apply", icon: UserPlus, description: "Submit applicant details" },
  { label: "Settings", path: "/settings", icon: Settings, description: "Account & API config" },
]

