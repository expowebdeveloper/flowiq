import type { ReactNode } from "react"
import { Outlet } from "react-router-dom"
import { Sidebar } from "./Sidebar"
import { Topbar } from "./Topbar"
import { MobileNav } from "./MobileNav"

interface AppLayoutProps {
  /** When rendered directly (not as a nested route), pass the page content here instead of relying on <Outlet />. */
  children?: ReactNode
}

export function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="flex h-svh overflow-hidden bg-background">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <MobileNav />
        <main className="scrollbar-thin flex-1 overflow-y-auto p-4 md:p-6">
          <div className="mx-auto max-w-[100rem]">
            {children ?? <Outlet />}
          </div>
        </main>
      </div>
    </div>
  )
}
