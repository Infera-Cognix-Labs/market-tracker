"use client"

import { useCallback, useEffect, useState } from "react"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { T, css } from "./shared/DesignTokens"
import { FontLoader } from "./shared/FontLoader"
import { Sidebar } from "./shared/Sidebar"
import { DashboardPage } from "./dashboard/DashboardPage"
import { CategoryPage } from "./categories/CategoryPage"
import { CompetitorPage } from "./competitors/CompetitorPage"
import { EventsPage } from "./alerts/EventsPage"
import { ReportsPage } from "./reports/ReportsPage"

type PageKey = "dashboard" | "categories" | "competitors" | "events" | "reports"
const PAGE_KEYS: PageKey[] = ["dashboard", "categories", "competitors", "events", "reports"]

const toPageKey = (value: string | null): PageKey => {
  return PAGE_KEYS.includes(value as PageKey) ? value as PageKey : "dashboard"
}

export default function App() {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const [page, setPageState] = useState<PageKey>(() => toPageKey(searchParams.get("page")))

  useEffect(() => {
    setPageState(toPageKey(searchParams.get("page")))
  }, [searchParams])

  const setPage = useCallback((nextPage: string) => {
    const safePage = toPageKey(nextPage)
    const params = new URLSearchParams(searchParams.toString())
    if (safePage === "dashboard") params.delete("page")
    else params.set("page", safePage)
    setPageState(safePage)
    const query = params.toString()
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false })
  }, [pathname, router, searchParams])

  const pages: Record<PageKey, React.ReactNode> = {
    dashboard: <DashboardPage setPage={setPage} />,
    categories: <CategoryPage />,
    competitors: <CompetitorPage />,
    events: <EventsPage />,
    reports: <ReportsPage />,
  }

  return (
    <>
      <FontLoader />
      <style>{css}</style>
      <div style={{ display: "flex", minHeight: "100vh", background: T.bg0 }}>
        <Sidebar page={page} setPage={setPage} />
        <main style={{ flex: 1, minWidth: 0, padding: "28px 28px", overflowX: "auto" }}>
          {pages[page]}
        </main>
      </div>
    </>
  )
}
