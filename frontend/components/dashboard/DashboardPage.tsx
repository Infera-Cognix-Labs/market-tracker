"use client"

import { useEffect, useState } from "react"
import { Bell, BarChart2, Package, RefreshCw, ChevronRight, TrendingUp, AlertTriangle, Zap, Star, TrendingDown, ArrowUpRight } from "lucide-react"
import { T } from "../shared/DesignTokens"
import { PageHeader } from "../shared/PageHeader"
import { KPICard } from "../shared/KPICard"
import { Badge } from "../shared/Badge"
import { AlertTypeMeta } from "../shared/AlertTypeMeta"
import { apiGetDashboardOverview, apiListWeeklyDigests } from "../shared/api"
import type { DashboardOverview, Timeframe, WeeklyDigest } from "../shared/types"

export const DashboardPage = ({ setPage }: { setPage: (page: string) => void }) => {
  const [timeframe, setTimeframe] = useState<Timeframe>("WEEKLY")
  const [data, setData] = useState<DashboardOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [digest, setDigest] = useState<WeeklyDigest | null>(null)
  const [digestLoading, setDigestLoading] = useState(false)

  useEffect(() => {
    apiGetDashboardOverview(timeframe).then(d => { setData(d); setLoading(false) })
  }, [timeframe])

  const handleWeeklyDigest = async () => {
    setDigestLoading(true)
    const res = await apiListWeeklyDigests()
    setDigest(res.items[0] || null)
    setDigestLoading(false)
  }

  if (loading || !data) return <div style={{ textAlign: "center", padding: 60, color: T.text3 }}>Loading dashboard...</div>

  const s = data.summary

  return (
    <div className="anim-fade">
      <PageHeader title="Dashboard" sub={`Generated at ${new Date(data.generated_at).toLocaleString()} — ${data.timeframe} view`}
        actions={<button className="btn-ghost" onClick={() => apiGetDashboardOverview(timeframe).then(d => setData(d))}><RefreshCw size={14} /> Refresh</button>} />

      {/* Timeframe selector */}
      <div style={{ display: "flex", gap: 4, marginBottom: 16 }}>
        {(["DAILY", "WEEKLY", "MONTHLY"] as Timeframe[]).map(t => (
          <button key={t} onClick={() => setTimeframe(t)} style={{ padding: "5px 12px", borderRadius: 6, border: `1px solid ${t === timeframe ? T.amber : T.border}`, background: t === timeframe ? T.bg4 : "transparent", color: t === timeframe ? T.amber : T.text3, fontSize: 11, fontWeight: 600, cursor: "pointer", textTransform: "capitalize" }}>
            {t.toLowerCase()}
          </button>
        ))}
      </div>

      {/* KPIs */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 20 }}>
        <KPICard label="Category Trackers" value={s.active_category_tracker_count} sub="active" icon={<BarChart2 size={16} />} accent={T.blue} />
        <KPICard label="Competitor Trackers" value={s.active_competitor_tracker_count} sub="active" icon={<Package size={16} />} accent={T.teal} />
        <KPICard label="Tracked Products" value={s.tracked_product_count} sub="across all trackers" icon={<Package size={16} />} accent={T.green} />
        <KPICard label="Events This Period" value={s.new_entrant_count + s.returning_count + s.top10_enter_count + s.price_change_count + s.listing_change_count} sub="total signals" icon={<Bell size={16} />} accent={T.amber} />
      </div>

      {/* Event breakdown mini-cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 10, marginBottom: 20 }}>
        {[
          { label: "New Entrants", value: s.new_entrant_count, color: T.green, icon: <Zap size={13} /> },
          { label: "Returning", value: s.returning_count, color: "#90EE90", icon: <RefreshCw size={13} /> },
          { label: "Top 10 Entry", value: s.top10_enter_count, color: T.amber, icon: <Star size={13} /> },
          { label: "Price Changes", value: s.price_change_count, color: T.blue, icon: <TrendingDown size={13} /> },
          { label: "Listing Changes", value: s.listing_change_count, color: T.purple, icon: <TrendingUp size={13} /> },
        ].map(m => (
          <div key={m.label} className="card" style={{ padding: "10px 14px", display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ width: 28, height: 28, borderRadius: 6, background: `${m.color}18`, display: "flex", alignItems: "center", justifyContent: "center", color: m.color }}>{m.icon}</div>
            <div>
              <span style={{ fontSize: 20, fontWeight: 700, fontFamily: T.mono, color: m.color }}>{m.value}</span>
              <div style={{ fontSize: 10, color: T.text2 }}>{m.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Highlights + Threats */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
        {/* Category Highlights */}
        <div className="card">
          <div style={{ fontSize: 13, fontWeight: 600, color: T.text1, marginBottom: 14 }}>Category Highlights</div>
          {data.category_highlights.map(h => (
            <div key={h.tracker_code} style={{ padding: "10px 0", borderBottom: `1px solid ${T.border}` }}>
              <div style={{ fontSize: 12, color: T.text0, fontWeight: 500, marginBottom: 6 }}>{h.tracker_name}</div>
              <div style={{ display: "flex", gap: 12, fontSize: 11 }}>
                <span style={{ color: T.green }}>+{h.new_entrant_count} new</span>
                <span style={{ color: T.red }}>−{h.exit_count} exits</span>
                <span style={{ color: T.amber }}>★{h.top10_enter_count} top10</span>
              </div>
            </div>
          ))}
          {data.competitor_highlights.map(h => (
            <div key={h.tracker_code} style={{ padding: "10px 0", borderBottom: `1px solid ${T.border}` }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                <span style={{ fontSize: 12, color: T.text0, fontWeight: 500 }}>{h.tracker_name}</span>
                <Badge type="info" text="Competitor" />
              </div>
              <div style={{ display: "flex", gap: 12, fontSize: 11 }}>
                <span style={{ color: T.blue }}>💰{h.price_change_count} price</span>
                <span style={{ color: T.purple }}>📦{h.availability_change_count} stock</span>
                <span style={{ color: T.teal }}>📝{h.listing_change_count} listing</span>
              </div>
            </div>
          ))}
          <button className="btn-ghost" style={{ width: "100%", justifyContent: "center", marginTop: 10, fontSize: 12 }} onClick={() => setPage("categories")}>
            View categories <ChevronRight size={13} />
          </button>
        </div>

        {/* Top Threats */}
        <div className="card">
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
            <AlertTriangle size={14} style={{ color: T.red }} />
            <span style={{ fontSize: 13, fontWeight: 600, color: T.text1 }}>Top Threats</span>
          </div>
          {data.top_threats.length === 0 && (
            <div style={{ textAlign: "center", padding: "30px 0", color: T.text3, fontSize: 12 }}>No threats detected this period</div>
          )}
          {data.top_threats.map((threat, i) => (
            <div key={i} style={{ padding: "12px 0", borderBottom: i < data.top_threats.length - 1 ? `1px solid ${T.border}` : "none" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                <span style={{ fontFamily: T.mono, fontSize: 11, color: T.amber, fontWeight: 600 }}>{threat.asin}</span>
                <span style={{ fontSize: 10, color: T.text3, fontFamily: T.mono }}>{threat.marketplace}</span>
              </div>
              <div style={{ fontSize: 12, color: T.text0, marginBottom: 6 }}>{threat.reason}</div>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {threat.event_types?.map(et => {
                  const meta = AlertTypeMeta(et)
                  return <Badge key={et} type={meta.badgeType} text={meta.label} />
                })}
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 6, fontSize: 10, color: T.text3 }}>
                {threat.tracker_refs.map(tr => (
                  <span key={tr.tracker_code}>{tr.tracker_name}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Weekly Digest */}
      <div className="card" style={{ marginBottom: 16 }}>
        <button className="btn-primary" onClick={handleWeeklyDigest} disabled={digestLoading}
          style={{ width: "100%", justifyContent: "center", marginBottom: digest ? 12 : 0 }}>
          <TrendingUp size={14} /> {digestLoading ? "Loading..." : "Load Weekly Digest"}
        </button>
        {digest && (
          <div style={{ background: `${T.green}18`, border: `1px solid ${T.green}40`, borderRadius: 8, padding: 16 }}>
            <div style={{ fontWeight: 700, color: T.green, fontSize: 13, marginBottom: 10 }}>
              Weekly Digest — {digest.week_start} to {digest.week_end}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 10, marginBottom: 12 }}>
              {[
                { l: "New Entrants", v: digest.summary.new_entrant_count },
                { l: "Returning", v: digest.summary.returning_count },
                { l: "Top 10 Entry", v: digest.summary.top10_enter_count },
                { l: "Price Changes", v: digest.summary.price_change_count },
                { l: "Listing Changes", v: digest.summary.listing_change_count },
              ].map(k => (
                <div key={k.l} style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 18, fontWeight: 700, fontFamily: T.mono, color: T.text0 }}>{k.v}</div>
                  <div style={{ fontSize: 9, color: T.text2 }}>{k.l}</div>
                </div>
              ))}
            </div>
            {digest.threats.length > 0 && (
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, color: T.amber, marginBottom: 6 }}>Threats</div>
                {digest.threats.map((t, i) => (
                  <div key={i} style={{ fontSize: 11, color: T.text0, marginBottom: 4 }}>
                    <span style={{ fontFamily: T.mono, color: T.amber }}>{t.asin}</span> — {t.reason}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Recent Events */}
      <div className="card">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: T.text1 }}>Recent Events</span>
          <button className="btn-ghost" onClick={() => setPage("events")} style={{ fontSize: 12 }}>View all <ChevronRight size={13} /></button>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
          {data.top_events.slice(0, 6).map(ev => {
            const meta = AlertTypeMeta(ev.event_type)
            return (
              <div key={ev.event_code} className="row-hover" style={{ display: "flex", alignItems: "center", gap: 12, padding: "9px 8px", borderRadius: 7 }}>
                <span style={{ color: meta.color, flexShrink: 0 }}>{meta.icon}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12, color: T.text0, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{ev.title}</div>
                  <div style={{ fontSize: 11, color: T.text2, marginTop: 1 }}>{ev.summary}</div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                  <Badge type={meta.badgeType} text={meta.label} />
                  <Badge type={ev.severity === "HIGH" ? "exit" : ev.severity === "MEDIUM" ? "top10" : "info"} text={ev.severity} />
                  <span style={{ fontSize: 10, fontFamily: T.mono, color: T.text3 }}>{ev.asin}</span>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
