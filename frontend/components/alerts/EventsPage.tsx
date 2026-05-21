"use client"

import { useState, useEffect } from "react"
import { ChevronLeft, ChevronRight, Filter } from "lucide-react"
import { T } from "../shared/DesignTokens"
import { PageHeader } from "../shared/PageHeader"
import { Badge } from "../shared/Badge"
import { AlertTypeMeta } from "../shared/AlertTypeMeta"
import { apiListEvents } from "../shared/api"
import type { Event, EventType, Severity } from "../shared/types"

const EVENT_TYPES: EventType[] = [
  "NEW_ENTRANT_TOP50", "RETURNING_TOP50", "EXIT_TOP50",
  "ENTER_TOP10", "EXIT_TOP10",
  "PRICE_CHANGED", "PROMOTION_CHANGED",
  "TITLE_CHANGED", "MAIN_IMAGE_CHANGED", "VARIATIONS_ADDED", "CONTENT_CHANGED",
  "AVAILABILITY_CHANGED", "BUY_BOX_CHANGED",
]
const SEVERITIES: Severity[] = ["HIGH", "MEDIUM", "LOW"]

export const EventsPage = () => {
  const [events, setEvents] = useState<Event[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPageNum] = useState(1)
  const [loading, setLoading] = useState(true)
  const [filterType, setFilterType] = useState<EventType | "">("")
  const [filterSeverity, setFilterSeverity] = useState<Severity | "">("")

  const loadEvents = (p: number) => {
    setLoading(true)
    apiListEvents({
      event_type: filterType || undefined,
      severity: filterSeverity || undefined,
      page: p,
      page_size: 20,
    }).then(res => {
      setEvents(res.items)
      setTotal(res.total)
      setPageNum(p)
      setLoading(false)
    })
  }

  useEffect(() => {
    apiListEvents({
      event_type: filterType || undefined,
      severity: filterSeverity || undefined,
      page: 1,
      page_size: 20,
    }).then(res => {
      setEvents(res.items)
      setTotal(res.total)
      setPageNum(1)
      setLoading(false)
    })
  }, [filterType, filterSeverity])

  return (
    <div className="anim-fade">
      <PageHeader title="Events" sub={`${total} events detected`} />

      {/* Filters */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap", alignItems: "center" }}>
        <Filter size={13} style={{ color: T.text3 }} />

        {/* Severity filter */}
        <div style={{ display: "flex", gap: 4 }}>
          {SEVERITIES.map(sev => {
            const active = filterSeverity === sev
            const sevColor = sev === "HIGH" ? T.red : sev === "MEDIUM" ? T.amber : T.text2
            return (
              <button key={sev} onClick={() => setFilterSeverity(active ? "" : sev)}
                style={{ padding: "5px 10px", borderRadius: 6, border: `1px solid ${active ? sevColor : T.border}`, background: active ? T.bg4 : T.bg2, color: active ? sevColor : T.text2, fontSize: 11, fontWeight: 600, cursor: "pointer", transition: "all .15s" }}>
                {sev}
              </button>
            )
          })}
        </div>

        <span style={{ color: T.border2, margin: "0 4px" }}>|</span>

        {/* Event type filter */}
        <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
          {EVENT_TYPES.map(et => {
            const meta = AlertTypeMeta(et)
            const active = filterType === et
            return (
              <button key={et} onClick={() => setFilterType(active ? "" : et)}
                style={{ display: "flex", alignItems: "center", gap: 4, padding: "5px 8px", borderRadius: 6, border: `1px solid ${active ? meta.color : T.border}`, background: active ? T.bg4 : T.bg2, cursor: "pointer", transition: "all .15s" }}>
                <span style={{ color: meta.color, display: "flex" }}>{meta.icon}</span>
                <span style={{ fontSize: 10, color: active ? meta.color : T.text2, fontFamily: T.mono }}>{meta.label}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Events list */}
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {loading && <div style={{ textAlign: "center", padding: 40, color: T.text3 }}>Loading events...</div>}
        {!loading && events.length === 0 && (
          <div style={{ textAlign: "center", padding: "40px 0", color: T.text3, fontSize: 13 }}>No events match this filter</div>
        )}
        {!loading && events.map(ev => {
          const meta = AlertTypeMeta(ev.event_type)
          return (
            <div key={ev.event_code}
              style={{ background: T.bg2, border: `1px solid ${T.border}`, borderLeft: `3px solid ${meta.color}`, borderRadius: 8, padding: "12px 16px", display: "flex", alignItems: "center", gap: 14, transition: "all .15s" }}
              className="row-hover">
              <div style={{ width: 32, height: 32, borderRadius: 8, background: `${meta.color}18`, display: "flex", alignItems: "center", justifyContent: "center", color: meta.color, flexShrink: 0 }}>
                {meta.icon}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 3 }}>
                  <Badge type={meta.badgeType} text={meta.label} />
                  <Badge type={ev.severity === "HIGH" ? "exit" : ev.severity === "MEDIUM" ? "top10" : "info"} text={ev.severity} />
                  <span style={{ fontSize: 9, fontFamily: T.mono, color: T.text3, padding: "1px 5px", background: T.bg4, borderRadius: 3 }}>
                    {ev.tracker_type}
                  </span>
                </div>
                <div style={{ fontSize: 13, color: T.text0, fontWeight: 500 }}>{ev.title}</div>
                <div style={{ fontSize: 12, color: T.text2, marginTop: 2 }}>{ev.summary}</div>
              </div>
              <div style={{ textAlign: "right", flexShrink: 0 }}>
                <div style={{ fontSize: 10, fontFamily: T.mono, color: T.text3 }}>{new Date(ev.event_time).toLocaleString()}</div>
                <div style={{ fontSize: 10, fontFamily: T.mono, color: T.amber, marginTop: 2 }}>{ev.asin}</div>
                <div style={{ fontSize: 9, fontFamily: T.mono, color: T.text3, marginTop: 2 }}>{ev.tracker_code}</div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Pagination */}
      {total > 20 && (
        <div style={{ display: "flex", justifyContent: "center", gap: 8, marginTop: 16 }}>
          <button className="btn-ghost" disabled={page <= 1} onClick={() => loadEvents(page - 1)}>
            <ChevronLeft size={14} /> Prev
          </button>
          <span style={{ fontSize: 11, color: T.text3, fontFamily: T.mono, padding: "6px 10px" }}>
            Page {page} of {Math.ceil(total / 20)}
          </span>
          <button className="btn-ghost" disabled={page >= Math.ceil(total / 20)} onClick={() => loadEvents(page + 1)}>
            Next <ChevronRight size={14} />
          </button>
        </div>
      )}
    </div>
  )
}
