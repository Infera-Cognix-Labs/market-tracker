"use client"

import { useState } from "react"
import { T, css } from "./shared/DesignTokens"
import { FontLoader } from "./shared/FontLoader"
import { Sidebar } from "./shared/Sidebar"
import { DashboardPage } from "./dashboard/DashboardPage"
import { CategoryPage } from "./categories/CategoryPage"
import { CompetitorPage } from "./competitors/CompetitorPage"
import { EventsPage } from "./alerts/EventsPage"
import { JobsPage } from "./jobs/JobsPage"
import { ReportsPage } from "./reports/ReportsPage"
import { NodeSearchPage } from "./search/NodeSearchPage"

type PageKey = "dashboard" | "categories" | "competitors" | "events" | "jobs" | "reports" | "search"

export default function App() {
  const [page, setPage] = useState<PageKey>("dashboard")

  const pages: Record<PageKey, React.ReactNode> = {
    dashboard: <DashboardPage setPage={setPage as (page: string) => void} />,
    categories: <CategoryPage />,
    competitors: <CompetitorPage />,
    events: <EventsPage />,
    jobs: <JobsPage />,
    reports: <ReportsPage />,
    search: <NodeSearchPage />,
  }

  return (
    <>
      <FontLoader />
      <style>{css}</style>
      <div style={{ display: "flex", minHeight: "100vh", background: T.bg0 }}>
        <Sidebar page={page} setPage={setPage as (page: string) => void} />
        <main style={{ flex: 1, minWidth: 0, padding: "28px 28px", overflowX: "auto" }}>
          {pages[page]}
        </main>
      </div>
    </>
  )
}
