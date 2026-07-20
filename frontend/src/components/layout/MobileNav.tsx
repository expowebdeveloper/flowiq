import { NavLink } from "react-router-dom"
import { navItems } from "@/config/navigation"
import { useAuth } from "@/contexts/AuthContext"
import { useBankNotifications } from "@/contexts/BankNotificationsContext"
import { cn } from "@/lib/utils"

export function MobileNav() {
  const { user } = useAuth()
  const { unreadCount } = useBankNotifications()
  const isBank = user?.role === "bank"
  const visibleItems = navItems.filter(
    (item) => (!item.brokerOnly || !isBank) && (!item.bankOnly || isBank),
  )

  return (
    <nav className="flex shrink-0 items-center gap-1 overflow-x-auto border-b border-border bg-background px-2 py-1.5 md:hidden">
      {visibleItems.map((item) => (
        <NavLink
          key={item.path}
          to={item.path}
          end={item.path === "/"}
          className={({ isActive }) =>
            cn(
              "flex shrink-0 items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors",
              isActive
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-accent/50",
            )
          }
        >
          <item.icon className="size-3.5" />
          {item.label}
          {item.bankOnly && unreadCount > 0 && (
            <span className="flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-medium text-destructive-foreground">
              {unreadCount > 99 ? "99+" : unreadCount}
            </span>
          )}
        </NavLink>
      ))}
    </nav>
  )
}
