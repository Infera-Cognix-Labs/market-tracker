"use client"

import { useCallback, useState } from "react"
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
const PAGE_STORAGE_KEY = "market_tracker_active_page"

const toPageKey = (value: string | null): PageKey => {
  return PAGE_KEYS.includes(value as PageKey) ? value as PageKey : "dashboard"
}

export default function App() {
  const [page, setPageState] = useState<PageKey>(() => {
    if (typeof window === "undefined") return "dashboard"
    return toPageKey(window.sessionStorage.getItem(PAGE_STORAGE_KEY))
  })

  const setPage = useCallback((nextPage: string) => {
    const safePage = toPageKey(nextPage)
    window.sessionStorage.setItem(PAGE_STORAGE_KEY, safePage)
    setPageState(safePage)
  }, [])

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
