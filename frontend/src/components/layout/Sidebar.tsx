import { NavLink } from "react-router-dom"
import { Zap } from "lucide-react"
import { navItems } from "@/config/navigation"
import { useAuth } from "@/contexts/AuthContext"
import { useBankNotifications } from "@/contexts/BankNotificationsContext"
import { cn } from "@/lib/utils"

export function Sidebar() {
  const { user } = useAuth()
  const { unreadCount } = useBankNotifications()
  const isBank = user?.role === "bank"
  const visibleItems = navItems.filter(
    (item) => (!item.brokerOnly || !isBank) && (!item.bankOnly || isBank),
  )

  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground md:flex">
      <div className="flex h-14 items-center gap-2 px-5">
        <div className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <Zap className="size-4" />
        </div>
        <span className="text-sm font-semibold tracking-tight">FlowIQ Console</span>
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-2">
        {visibleItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground",
              )
            }
          >
            <item.icon className="size-4 shrink-0" />
            <span className="flex-1">{item.label}</span>
            {item.bankOnly && unreadCount > 0 && (
              <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-destructive px-1.5 text-xs font-medium text-destructive-foreground">
                {unreadCount > 99 ? "99+" : unreadCount}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-sidebar-border px-5 py-3 text-xs text-sidebar-foreground/50">
        API Tester v1.0
      </div>
    </aside>
  )
}
