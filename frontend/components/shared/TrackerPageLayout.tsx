"use client"

import { Edit2, Plus } from "lucide-react"
import { EventsStatusBanner } from "./EventsStatusBanner"
import { KpiFilterBar } from "./KpiFilterBar"
import { PageHeader } from "./PageHeader"
import { StatusFilterTabs } from "./StatusFilterTabs"
import { TrackerSelector } from "./TrackerSelector"
import type { CategorySnapshot } from "./types"
import type { EventsState } from "./hooks"

interface TrackerPageLayoutProps {
  title: string
  sub: string
  trackers: { tracker_code: string; name: string; status?: string }[]
  selectedCode: string
  statusFilter: string
  onStatusFilterChange: (v: string) => void
  onSelectTracker: (code: string) => void
  onEdit: () => void
  onCreate: () => void
  selectedTracker?: { name: string; status?: string; tracking_config?: { top_n: number }; schedule?: { frequency: string; hour_utc: number }; stats?: { last_success_at?: string | null; snapshot_count?: number } }
  snapshot: CategorySnapshot | null
  activeKpiFilter: string
  onKpiFilterChange: (f: string) => void
  eventsState: EventsState
  onEventsRetry: () => void
  children?: React.ReactNode
}

export const TrackerPageLayout = ({
  title,
  sub,
  trackers,
  selectedCode,
  statusFilter,
  onStatusFilterChange,
  onSelectTracker,
  onEdit,
  onCreate,
  selectedTracker,
  snapshot,
  activeKpiFilter,
  onKpiFilterChange,
  eventsState,
  onEventsRetry,
  children,
}: TrackerPageLayoutProps) => (
  <div className="anim-fade">
    <PageHeader title={title} sub={sub}
      actions={
        <div style={{ display: "flex", gap: 8 }}>
          {selectedTracker && (
            <button className="btn-ghost" onClick={onEdit}
              style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
              <Edit2 size={14} /> Edit Tracker
            </button>
          )}
          <button className="btn-primary" onClick={onCreate}
            style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <Plus size={14} /> New Tracker
          </button>
        </div>
      } />

    <StatusFilterTabs trackers={trackers} value={statusFilter} onChange={onStatusFilterChange} />
    <TrackerSelector trackers={trackers} statusFilter={statusFilter} selectedCode={selectedCode} onSelect={onSelectTracker} />

    {children}

    {snapshot && (
      <KpiFilterBar
        summary={{
          asin_count: snapshot.summary.asin_count,
          new_entrants: snapshot.summary.new_entrant_count,
          returning: snapshot.summary.returning_count,
          exits: snapshot.summary.exit_count,
          enter_top10: snapshot.summary.enter_top10_count,
          exit_top10: snapshot.summary.exit_top10_count,
        }}
        activeFilter={activeKpiFilter}
        onFilterChange={onKpiFilterChange}
      />
    )}

    <EventsStatusBanner loading={eventsState.loading} error={eventsState.error} onRetry={onEventsRetry} />
  </div>
)
