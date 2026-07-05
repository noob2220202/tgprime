import { NavLink, Outlet } from "react-router-dom"
import { Users, Wand2, History, MessageCircle, Bot, LogOut, Moon, Sun } from "lucide-react"
import { cn } from "../lib/utils"
import { useLogout } from "../hooks/useAuth"
import { useTheme } from "../hooks/useTheme"
import { Button } from "./ui/button"

const NAV_ITEMS = [
  { to: "/accounts", label: "계정", icon: Users },
  { to: "/chat", label: "채팅", icon: MessageCircle },
  { to: "/bulk-edit", label: "일괄 편집", icon: Wand2 },
  { to: "/auto-reply", label: "자동응답", icon: Bot },
  { to: "/jobs", label: "작업 이력", icon: History },
]

export function Layout() {
  const logoutMutation = useLogout()
  const { theme, toggle } = useTheme()

  return (
    <div className="flex min-h-svh">
      <aside className="flex w-56 shrink-0 flex-col border-r border-border bg-sidebar">
        <div className="flex items-center justify-between px-4 py-4">
          <span className="text-base font-semibold">Telegram Prime</span>
          <button
            onClick={toggle}
            aria-label="테마 전환"
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </div>
        <nav className="flex flex-1 flex-col gap-1 px-2">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm text-foreground/80 hover:bg-muted",
                  isActive && "bg-muted font-medium text-foreground"
                )
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-2">
          <Button variant="ghost" size="sm" className="w-full justify-start" onClick={() => logoutMutation.mutate()}>
            <LogOut size={16} />
            로그아웃
          </Button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
