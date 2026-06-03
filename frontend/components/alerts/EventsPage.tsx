"use client"

import { useState, useEffect, useCallback } from "react"
import { ChevronLeft, ChevronRight, Filter, Send } from "lucide-react"
import { T } from "../shared/DesignTokens"
import { PageHeader } from "../shared/PageHeader"
import { Badge } from "../shared/Badge"
import { AlertTypeMeta } from "../shared/AlertTypeMeta"
import { apiListEvents, apiGetProductDetail } from "../shared/api"
import type { Event, EventType, Severity } from "../shared/types"

const EVENT_TYPES: EventType[] = [
  "NEW_ENTRANT_TOP50", "RETURNING_TOP50", "EXIT_TOP50",
  "ENTER_TOP10", "EXIT_TOP10",
  "PRICE_CHANGED", "PROMOTION_CHANGED",
  "TITLE_CHANGED", "MAIN_IMAGE_CHANGED", "VARIATIONS_ADDED", "CONTENT_CHANGED",
  "AVAILABILITY_CHANGED", "BUY_BOX_CHANGED",
]
const SEVERITIES: Severity[] = ["HIGH", "MEDIUM", "LOW"]

type DatePreset = "all" | "today" | "7d" | "30d" | "custom"

const toISODate = (d: Date) => d.toISOString().slice(0, 10)

const presetRange = (preset: DatePreset): { from: string; to: string } | null => {
  if (preset === "all" || preset === "custom") return null
  const now = new Date()
  const to = toISODate(now)
  if (preset === "today") return { from: to, to }
  const from = new Date(now)
  from.setDate(from.getDate() - (preset === "7d" ? 7 : 30))
  return { from: toISODate(from), to }
}

export const EventsPage = () => {
  const [events, setEvents] = useState<Event[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPageNum] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filterType, setFilterType] = useState<EventType | "">("")
  const [filterSeverity, setFilterSeverity] = useState<Severity | "">("")
  const [datePreset, setDatePreset] = useState<DatePreset>("all")
  const [customFrom, setCustomFrom] = useState("")
  const [customTo, setCustomTo] = useState("")
  const [productImages, setProductImages] = useState<Map<string, string>>(new Map())
  const [slackStatus, setSlackStatus] = useState<Map<string, "sending" | "done" | "error">>(new Map())
  const [webhookUrl, setWebhookUrl] = useState("")
  const [showWebhookInput, setShowWebhookInput] = useState(false)

  const loadEvents = useCallback(async (p: number) => {
    setLoading(true)
    setError(null)
    try {
      let fromDate: string | undefined
      let toDate: string | undefined
      if (datePreset === "custom") {
        fromDate = customFrom || undefined
        toDate = customTo || undefined
      } else {
        const range = presetRange(datePreset)
        fromDate = range?.from
        toDate = range?.to
      }
      const res = await apiListEvents({
        event_type: filterType || undefined,
        severity: filterSeverity || undefined,
        from_date: fromDate,
        to_date: toDate,
        page: p,
        page_size: 20,
      })
      setEvents(res.items)
      setTotal(res.total)
      setPageNum(p)

      // Batch-fetch product images for unique ASINs on this page
      const pairs = [...new Map(res.items.map(e => [`${e.marketplace}:${e.asin}`, e])).values()]
      const results = await Promise.allSettled(
        pairs.map(e => apiGetProductDetail(e.marketplace, e.asin))
      )
      const imgMap = new Map<string, string>()
      results.forEach((r, i) => {
        if (r.status === "fulfilled" && r.value?.main_image_url_latest) {
          imgMap.set(`${pairs[i].marketplace}:${pairs[i].asin}`, r.value.main_image_url_latest)
        }
      })
      setProductImages(imgMap)
    } catch {
      setEvents([])
      setTotal(0)
      setPageNum(p)
      setError("Failed to load events")
    } finally {
      setLoading(false)
    }
  }, [filterType, filterSeverity, datePreset, customFrom, customTo])

  useEffect(() => {
    void loadEvents(1)
  }, [loadEvents])

  useEffect(() => {
    const stored = localStorage.getItem("slack_webhook_url")
    if (stored) setWebhookUrl(stored)
  }, [])

  const sendToSlack = useCallback(async (ev: Event) => {
    if (!webhookUrl) {
      alert("Please set Slack webhook URL first")
      return
    }
    const status = new Map(slackStatus)
    status.set(ev.event_code, "sending")
    setSlackStatus(status)
    try {
      const color = ev.severity === "HIGH" ? "danger" : ev.severity === "MEDIUM" ? "warning" : "#36a64f"
      const payload = {
        text: `🔔 Event: ${ev.title}`,
        attachments: [
          {
            color,
            fields: [
              { title: "Type", value: ev.event_type, short: true },
              { title: "Severity", value: ev.severity, short: true },
              { title: "ASIN", value: ev.asin, short: true },
              { title: "Tracker", value: `${ev.tracker_code} (${ev.tracker_type})`, short: true },
              { title: "Product", value: ev.title, short: false },
              { title: "Summary", value: ev.summary || "N/A", short: false },
              { title: "Time", value: new Date(ev.event_time).toLocaleString(), short: true },
              { title: "Marketplace", value: ev.marketplace, short: true },
            ],
          },
        ],
      }
      await fetch(webhookUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        mode: "no-cors",
      })
      status.set(ev.event_code, "done")
      setTimeout(() => {
        const st = new Map(slackStatus)
        st.delete(ev.event_code)
        setSlackStatus(st)
      }, 2000)
    } catch {
      status.set(ev.event_code, "error")
      setSlackStatus(status)
    }
  }, [slackStatus, webhookUrl])

  return (
    <div className="anim-fade">
      <PageHeader title="Events" sub={`${total} events detected`} />

      {/* Slack Webhook Setting */}
      <div style={{ marginBottom: 12, padding: "8px 12px", borderRadius: 6, border: `1px solid ${T.border}`, background: T.bg2 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: showWebhookInput ? 8 : 0 }}>
          <span style={{ fontSize: 11, fontWeight: 600, color: T.text2 }}>🔗 Slack Webhook:</span>
          <span style={{ fontSize: 10, fontFamily: T.mono, color: T.text3 }}>
            {webhookUrl ? `${webhookUrl.slice(0, 40)}...` : "Not configured"}
          </span>
          <button
            onClick={() => setShowWebhookInput(!showWebhookInput)}
            style={{ marginLeft: "auto", padding: "4px 8px", borderRadius: 4, border: `1px solid ${T.border}`, background: T.bg3, color: T.text2, fontSize: 10, fontWeight: 500, cursor: "pointer", transition: "all .15s" }}
          >
            {showWebhookInput ? "Cancel" : "Edit"}
          </button>
        </div>
        {showWebhookInput && (
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              type="text"
              value={webhookUrl}
              onChange={e => setWebhookUrl(e.target.value)}
              placeholder="https://hooks.slack.com/services/..."
              style={{ flex: 1, padding: "6px 10px", borderRadius: 4, border: `1px solid ${T.border}`, background: T.bg3, color: T.text0, fontSize: 11, fontFamily: T.mono, outline: "none" }}
            />
            <button
              onClick={() => {
                localStorage.setItem("slack_webhook_url", webhookUrl)
                setShowWebhookInput(false)
              }}
              style={{ padding: "6px 12px", borderRadius: 4, border: `1px solid ${T.green}`, background: T.green, color: T.bg0, fontSize: 10, fontWeight: 600, cursor: "pointer", transition: "all .15s" }}
            >
              Save
            </button>
          </div>
        )}
      </div>

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

        {/* Date range filter */}
        <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
          {(["all", "today", "7d", "30d", "custom"] as DatePreset[]).map(p => (
            <button key={p} onClick={() => setDatePreset(p)}
              style={{ padding: "5px 10px", borderRadius: 6, border: `1px solid ${datePreset === p ? T.blue : T.border}`, background: datePreset === p ? T.bg4 : T.bg2, color: datePreset === p ? T.blue : T.text2, fontSize: 11, fontWeight: 600, cursor: "pointer", transition: "all .15s" }}>
              {p === "all" ? "All time" : p === "today" ? "Today" : p === "7d" ? "Last 7d" : p === "30d" ? "Last 30d" : "Custom"}
            </button>
          ))}
          {datePreset === "custom" && (
            <>
              <input type="date" value={customFrom} onChange={e => setCustomFrom(e.target.value)}
                style={{ padding: "4px 8px", borderRadius: 6, border: `1px solid ${T.border}`, background: T.bg2, color: T.text0, fontSize: 11, fontFamily: T.mono, cursor: "pointer" }} />
              <span style={{ color: T.text3, fontSize: 11 }}>→</span>
              <input type="date" value={customTo} onChange={e => setCustomTo(e.target.value)}
                style={{ padding: "4px 8px", borderRadius: 6, border: `1px solid ${T.border}`, background: T.bg2, color: T.text0, fontSize: 11, fontFamily: T.mono, cursor: "pointer" }} />
            </>
          )}
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
        {!loading && error && events.length === 0 && (
          <div style={{ textAlign: "center", padding: 24, color: T.red, fontSize: 12 }}>{error}</div>
        )}
        {loading && <div style={{ textAlign: "center", padding: 40, color: T.text3 }}>Loading events...</div>}
        {!loading && events.length === 0 && (
          <div style={{ textAlign: "center", padding: "40px 0", color: T.text3, fontSize: 13 }}>No events match this filter</div>
        )}
        {!loading && events.map(ev => {
          const meta = AlertTypeMeta(ev.event_type)
          const imageUrl = ev.payload.current?.main_image_url || ev.payload.previous?.main_image_url
            || productImages.get(`${ev.marketplace}:${ev.asin}`)
          return (
            <div key={ev.event_code}
              style={{ background: T.bg2, border: `1px solid ${T.border}`, borderLeft: `3px solid ${meta.color}`, borderRadius: 8, padding: "12px 16px", display: "flex", alignItems: "center", gap: 14, transition: "all .15s" }}
              className="row-hover">
              <div style={{ width: 40, height: 40, borderRadius: 8, background: T.bg3, border: `1px solid ${T.border}`, overflow: "hidden", display: "flex", alignItems: "center", justifyContent: "center", color: meta.color, flexShrink: 0 }}>
                {imageUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={imageUrl} alt={ev.asin} style={{ width: "100%", height: "100%", objectFit: "cover" }} onError={e => { (e.target as HTMLImageElement).style.display = "none" }} />
                ) : (
                  meta.icon
                )}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 3, flexWrap: "wrap" }}>
                  <Badge type={meta.badgeType} text={meta.label} />
                  <Badge type={ev.severity === "HIGH" ? "exit" : ev.severity === "MEDIUM" ? "top10" : "info"} text={ev.severity} />
                  <span style={{ fontSize: 9, fontFamily: T.mono, color: T.text3, padding: "1px 5px", background: T.bg4, borderRadius: 3 }}>
                    {ev.tracker_type}
                  </span>
                  {slackStatus.has(ev.event_code) && (
                    <span style={{ fontSize: 9, fontFamily: T.mono, color: slackStatus.get(ev.event_code) === "done" ? T.green : slackStatus.get(ev.event_code) === "error" ? T.red : T.amber, padding: "1px 5px", background: T.bg4, borderRadius: 3 }}>
                      {slackStatus.get(ev.event_code) === "done" ? "Sent ✓" : slackStatus.get(ev.event_code) === "error" ? "Failed ✗" : "Sending..."}
                    </span>
                  )}
                </div>
                <div style={{ fontSize: 13, color: T.text0, fontWeight: 500 }}>{ev.title}</div>
                <div style={{ fontSize: 12, color: T.text2, marginTop: 2 }}>{ev.summary}</div>
              </div>
              <div style={{ textAlign: "right", flexShrink: 0, display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8 }}>
                <div>
                  <div style={{ fontSize: 10, fontFamily: T.mono, color: T.text3 }}>{new Date(ev.event_time).toLocaleString()}</div>
                  <div style={{ fontSize: 10, fontFamily: T.mono, color: T.amber, marginTop: 2 }}>{ev.asin}</div>
                  <div style={{ fontSize: 9, fontFamily: T.mono, color: T.text3, marginTop: 2 }}>{ev.tracker_code}</div>
                </div>
                <button onClick={() => void sendToSlack(ev)} disabled={slackStatus.get(ev.event_code) === "sending"}
                  style={{ display: "flex", alignItems: "center", gap: 4, padding: "4px 8px", borderRadius: 4, border: `1px solid ${slackStatus.get(ev.event_code) === "error" ? T.red : slackStatus.get(ev.event_code) === "done" ? T.green : T.border}`, background: slackStatus.get(ev.event_code) === "error" ? T.bg4 : slackStatus.get(ev.event_code) === "done" ? T.bg4 : T.bg3, color: slackStatus.get(ev.event_code) === "error" ? T.red : slackStatus.get(ev.event_code) === "done" ? T.green : T.text3, fontSize: 10, fontWeight: 500, cursor: "pointer", transition: "all .2s" }}>
                  <Send size={10} />
                  {slackStatus.get(ev.event_code) === "sending" ? "..." : slackStatus.get(ev.event_code) === "done" ? "✓" : slackStatus.get(ev.event_code) === "error" ? "✗" : "Slack"}
                </button>
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
