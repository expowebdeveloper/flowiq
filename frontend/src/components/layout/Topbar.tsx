import { useLocation, useNavigate } from "react-router-dom"
import { ArrowLeft, Bell, LogOut, Moon, Sun } from "lucide-react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useAuth } from "@/contexts/AuthContext"
import { useTheme } from "@/contexts/ThemeContext"
import { useBankNotifications } from "@/contexts/BankNotificationsContext"
import { navItems } from "@/config/navigation"

export function Topbar() {
  const { user, email, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const { unreadCount } = useBankNotifications()
  const location = useLocation()
  const navigate = useNavigate()
  const isBank = user?.role === "bank"

  const current = navItems.find(
    (item) => item.path === location.pathname || (item.path !== "/" && location.pathname.startsWith(item.path)),
  )

  const displayEmail = user?.email ?? email ?? ""
  const initials = displayEmail ? displayEmail.slice(0, 2).toUpperCase() : "?"

  // location.key is "default" only for the very first history entry (a
  // fresh load / directly-typed URL); anything reached by navigating within
  // the app gets a generated key, so going back with navigate(-1) lands
  // somewhere real instead of leaving the app. No back button on the
  // dashboard itself — there's nowhere meaningful to go back to from home.
  const isDashboard = location.pathname === "/"
  const canGoBack = location.key !== "default"
  function handleBack() {
    if (canGoBack) navigate(-1)
    else navigate("/")
  }

  return (
    <header className="flex h-14 shrink-0 items-center gap-4 border-b border-border bg-background px-4 md:px-6">
      {!isDashboard && (
        <Button variant="ghost" size="icon" onClick={handleBack} aria-label="Go back">
          <ArrowLeft className="size-4" />
        </Button>
      )}

      <div className="flex-1">
        <h1 className="text-sm font-semibold">{current?.label ?? "Dashboard"}</h1>
        <p className="text-xs text-muted-foreground">{current?.description}</p>
      </div>

      {isBank && (
        <Button
          variant="ghost"
          size="icon"
          className="relative"
          onClick={() => navigate("/notifications")}
          aria-label={`Customer notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ""}`}
        >
          <Bell className="size-4" />
          {unreadCount > 0 && (
            <span className="absolute right-1 top-1 flex size-4 items-center justify-center rounded-full bg-destructive text-[10px] font-medium text-destructive-foreground">
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </Button>
      )}

      <Button variant="ghost" size="icon" onClick={toggleTheme} aria-label="Toggle theme">
        {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
      </Button>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button className="flex items-center gap-2 rounded-full outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <Avatar>
              <AvatarFallback>{initials}</AvatarFallback>
            </Avatar>
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuLabel className="flex flex-col gap-0.5">
            <span className="font-medium text-foreground">{displayEmail}</span>
            <span className="capitalize">{user?.role ?? "…"}</span>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={() => logout()} className="text-destructive">
            <LogOut className="size-4" /> Log out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  )
}
