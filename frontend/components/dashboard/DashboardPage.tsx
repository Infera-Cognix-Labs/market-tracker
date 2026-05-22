"use client"

import { useEffect, useState, type ReactNode } from "react"
import Image from "next/image"
import { Bell, BarChart2, Package, RefreshCw, ChevronRight, ChevronDown, TrendingUp, AlertTriangle, Zap, Star, TrendingDown } from "lucide-react"
import { T } from "../shared/DesignTokens"
import { PageHeader } from "../shared/PageHeader"
import { KPICard } from "../shared/KPICard"
import { Badge } from "../shared/Badge"
import { AlertTypeMeta } from "../shared/AlertTypeMeta"
import { apiGetDashboardOverview, apiListWeeklyDigests, apiGetCategoryInsights, apiGetCompetitorInsights, apiGetCompetitorAlerts } from "../shared/api"
import type { DashboardOverview, Timeframe, WeeklyDigest, CategoryInsights, CompetitorInsights, CompetitorAlertCounts } from "../shared/types"

export const DashboardPage = ({ setPage }: { setPage: (page: string) => void }) => {
  const [timeframe, setTimeframe] = useState<Timeframe>("WEEKLY")
  const [data, setData] = useState<DashboardOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [digest, setDigest] = useState<WeeklyDigest | null>(null)
  const [digestLoading, setDigestLoading] = useState(false)
  const [categoryInsights, setCategoryInsights] = useState<CategoryInsights | null>(null)
  const [competitorInsights, setCompetitorInsights] = useState<CompetitorInsights | null>(null)
  const [competitorAlerts, setCompetitorAlerts] = useState<CompetitorAlertCounts | null>(null)
  const [expandedCard, setExpandedCard] = useState<string | null>(null)
  const [cardPages, setCardPages] = useState<Record<string, number>>({})

  const toggleCard = (label: string) => {
    setExpandedCard(prev => prev === label ? null : label)
    setCardPages(prev => ({ ...prev, [label]: 0 }))
  }

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    apiGetDashboardOverview(timeframe)
      .then(d => {
        if (cancelled) return
        setData(d && typeof d === "object" ? d : null)
      })
      .catch(() => {
        if (cancelled) return
        setData(null)
        setError("Failed to load dashboard data")
      })
      .finally(() => {
        if (cancelled) return
        setLoading(false)
      })

    apiGetCategoryInsights(timeframe).then(d => { if (!cancelled) setCategoryInsights(d) }).catch(() => {})
    apiGetCompetitorInsights(timeframe).then(d => { if (!cancelled) setCompetitorInsights(d) }).catch(() => {})
    apiGetCompetitorAlerts().then(d => { if (!cancelled) setCompetitorAlerts(d) }).catch(() => {})

    return () => {
      cancelled = true
    }
  }, [timeframe])

  const handleRefresh = async () => {
    setLoading(true)
    setError(null)
    try {
      const d = await apiGetDashboardOverview(timeframe)
      setData(d && typeof d === "object" ? d : null)
    } catch {
      setData(null)
      setError("Failed to refresh dashboard data")
    } finally {
      setLoading(false)
    }
    apiGetCategoryInsights(timeframe).then(setCategoryInsights).catch(() => {})
    apiGetCompetitorInsights(timeframe).then(setCompetitorInsights).catch(() => {})
    apiGetCompetitorAlerts().then(setCompetitorAlerts).catch(() => {})
  }

  const handleWeeklyDigest = async () => {
    setDigestLoading(true)
    try {
      const res = await apiListWeeklyDigests()
      setDigest(res.items[0] || null)
    } catch {
      setDigest(null)
    } finally {
      setDigestLoading(false)
    }
  }

  const fmtDate = (iso: string) => new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
  const chip = (text: string, color: string, dim?: boolean) => (
    <span style={{ display: "inline-block", fontSize: 10, color, background: dim ? `${color}12` : `${color}20`, border: `1px solid ${color}30`, borderRadius: 4, padding: "1px 6px", fontFamily: T.mono, whiteSpace: "nowrap" }}>{text}</span>
  )

  function renderInsightPanel<T extends { asin: string; title: string; brand: string; image_url: string; tracker_name: string }>(
    label: string, items: T[], borderColor: string, chipsContent: (item: T) => ReactNode
  ): ReactNode {
    const page = cardPages[label] ?? 0
    const totalPages = Math.ceil(items.length / 10) || 1
    const paged = items.slice(page * 10, (page + 1) * 10)
    return (
      <div className="card" style={{ marginTop: 8, padding: "12px 14px", border: `1px solid ${borderColor}` }}>
        {items.length === 0
          ? <div style={{ textAlign: "center", padding: "12px 0", color: T.text3, fontSize: 12 }}>No data</div>
          : paged.map((item, i) => (
            <div key={`${item.asin}-${page * 10 + i}`} style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "10px 0", borderBottom: i < paged.length - 1 ? `1px solid ${T.border}` : "none" }}>
              <a href={`https://www.amazon.com/dp/${item.asin}`} target="_blank" rel="noopener noreferrer" style={{ flexShrink: 0, display: "block", marginTop: 2 }}>
                <Image unoptimized src={item.image_url} alt="" width={40} height={40} style={{ objectFit: "contain", borderRadius: 6, background: T.bg3, display: "block" }} onError={e => { (e.target as HTMLImageElement).style.visibility = "hidden" }} />
              </a>
              <div style={{ flex: 1, minWidth: 0 }}>
                <a href={`https://www.amazon.com/dp/${item.asin}`} target="_blank" rel="noopener noreferrer" style={{ fontSize: 12, color: T.text0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "block", textDecoration: "none", marginBottom: 2 }}>{item.title}</a>
                <div style={{ fontSize: 10, color: T.text2, marginBottom: 5 }}>
                  <a href={`https://www.amazon.com/s?k=${encodeURIComponent(item.brand)}`} target="_blank" rel="noopener noreferrer" style={{ color: T.text2, textDecoration: "none" }}>{item.brand}</a>
                  {" · "}
                  <a href={`https://www.amazon.com/dp/${item.asin}`} target="_blank" rel="noopener noreferrer" style={{ color: T.text3, textDecoration: "none", fontFamily: T.mono }}>{item.asin}</a>
                  {" · "}{item.tracker_name}
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4, alignItems: "center" }}>
                  {chipsContent(item)}
                </div>
              </div>
            </div>
          ))}
        {totalPages > 1 && (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 12, marginTop: 10, paddingTop: 10, borderTop: `1px solid ${T.border}` }}>
            <button className="btn-ghost" disabled={page === 0} onClick={() => setCardPages(p => ({ ...p, [label]: page - 1 }))} style={{ fontSize: 11, padding: "3px 8px" }}>← Prev</button>
            <span style={{ fontSize: 11, color: T.text2, fontFamily: T.mono }}>{page + 1} / {totalPages}</span>
            <button className="btn-ghost" disabled={page >= totalPages - 1} onClick={() => setCardPages(p => ({ ...p, [label]: page + 1 }))} style={{ fontSize: 11, padding: "3px 8px" }}>Next →</button>
          </div>
        )}
      </div>
    )
  }

  if (loading) return <div style={{ textAlign: "center", padding: 60, color: T.text3 }}>Loading dashboard...</div>

  if (!data) {
    return (
      <div style={{ textAlign: "center", padding: 60, color: T.text3 }}>
        {error || "No dashboard data available"}
      </div>
    )
  }

  const s = data.summary

  return (
    <div className="anim-fade">
      <PageHeader title="Dashboard" sub={`Generated at ${new Date(data.generated_at).toLocaleString()} — ${data.timeframe} view`}
        actions={<button className="btn-ghost" onClick={handleRefresh}><RefreshCw size={14} /> Refresh</button>} />

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

      {/* Category Insights */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: T.text3, marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.06em" }}>Category Insights</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
          {([
            { label: "Top 10 Entrants", value: categoryInsights?.new_top10_entrants.length ?? 0, color: T.amber, icon: <Star size={13} /> },
            { label: "First-Time Entrants", value: categoryInsights?.first_time_entrants.length ?? 0, color: T.green, icon: <Zap size={13} /> },
            { label: "Returning Entrants", value: categoryInsights?.returning_entrants.length ?? 0, color: "#90EE90", icon: <RefreshCw size={13} /> },
          ] as const).map(m => {
            const active = expandedCard === m.label
            return (
              <div key={m.label} className="card" onClick={() => toggleCard(m.label)}
                style={{ padding: "10px 14px", display: "flex", alignItems: "center", gap: 10, cursor: "pointer", border: `1px solid ${active ? m.color : T.border}`, transition: "border-color .15s" }}>
                <div style={{ width: 28, height: 28, borderRadius: 6, background: `${m.color}18`, display: "flex", alignItems: "center", justifyContent: "center", color: m.color }}>{m.icon}</div>
                <div style={{ flex: 1 }}>
                  <span style={{ fontSize: 20, fontWeight: 700, fontFamily: T.mono, color: m.color }}>{m.value}</span>
                  <div style={{ fontSize: 10, color: T.text2 }}>{m.label}</div>
                </div>
                <ChevronDown size={12} style={{ color: T.text3, transform: active ? "rotate(180deg)" : "none", transition: "transform .2s", flexShrink: 0 }} />
              </div>
            )
          })}
        </div>
        {/* Expanded panels */}
        {expandedCard === "Top 10 Entrants" && categoryInsights &&
          renderInsightPanel("Top 10 Entrants", categoryInsights.new_top10_entrants, `${T.amber}40`, item => (
            <>
              {chip(`#${item.current_rank}`, T.amber)}
              {item.previous_rank != null && chip(`prev #${item.previous_rank}`, T.text3, true)}
              {item.is_first_time_entrant && chip("First time", T.green)}
              {chip(fmtDate(item.entered_at), T.text3, true)}
            </>
          ))}
        {expandedCard === "First-Time Entrants" && categoryInsights &&
          renderInsightPanel("First-Time Entrants", categoryInsights.first_time_entrants, `${T.green}40`, item => (
            <>
              {chip(`#${item.current_rank}`, T.green)}
              {item.previous_rank != null && chip(`prev #${item.previous_rank}`, T.text3, true)}
              {chip(fmtDate(item.entered_at), T.text3, true)}
            </>
          ))}
        {expandedCard === "Returning Entrants" && categoryInsights &&
          renderInsightPanel("Returning Entrants", categoryInsights.returning_entrants, "#90EE9040", item => (
            <>
              {chip(`#${item.current_rank}`, "#90EE90")}
              {item.previous_rank != null && chip(`prev #${item.previous_rank}`, T.text3, true)}
              {chip(`absent ${item.days_absent}d`, T.amber)}
              {chip(fmtDate(item.entered_at), T.text3, true)}
            </>
          ))}
      </div>

      {/* Competitor Insights */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: T.text3, marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.06em" }}>Competitor Insights</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
          {([
            { label: "Price Changes", value: competitorInsights?.price_changes.length ?? 0, color: T.blue, icon: <TrendingDown size={13} /> },
            { label: "Promotions", value: competitorInsights?.promotions.length ?? 0, color: T.amber, icon: <Bell size={13} /> },
            { label: "Availability Changes", value: competitorInsights?.availability_changes.length ?? 0, color: T.red, icon: <Package size={13} /> },
            { label: "Variation Changes", value: competitorInsights?.variation_changes.length ?? 0, color: T.purple, icon: <TrendingUp size={13} /> },
          ] as const).map(m => {
            const active = expandedCard === m.label
            return (
              <div key={m.label} className="card" onClick={() => toggleCard(m.label)}
                style={{ padding: "10px 14px", display: "flex", alignItems: "center", gap: 10, cursor: "pointer", border: `1px solid ${active ? m.color : T.border}`, transition: "border-color .15s" }}>
                <div style={{ width: 28, height: 28, borderRadius: 6, background: `${m.color}18`, display: "flex", alignItems: "center", justifyContent: "center", color: m.color }}>{m.icon}</div>
                <div style={{ flex: 1 }}>
                  <span style={{ fontSize: 20, fontWeight: 700, fontFamily: T.mono, color: m.color }}>{m.value}</span>
                  <div style={{ fontSize: 10, color: T.text2 }}>{m.label}</div>
                </div>
                <ChevronDown size={12} style={{ color: T.text3, transform: active ? "rotate(180deg)" : "none", transition: "transform .2s", flexShrink: 0 }} />
              </div>
            )
          })}
        </div>
        {/* Expanded panels */}
        {expandedCard === "Price Changes" && competitorInsights &&
          renderInsightPanel("Price Changes", competitorInsights.price_changes, `${T.blue}40`, item => {
            const sym = item.currency === "EUR" ? "€" : item.currency === "GBP" ? "£" : "$"
            return (
              <>
                {item.previous_price != null && chip(`was ${sym}${item.previous_price.toFixed(2)}`, T.text3, true)}
                {item.current_price != null && chip(`now ${sym}${item.current_price.toFixed(2)}`, T.blue)}
                {item.delta_pct != null && chip(`Δ ${item.delta_pct > 0 ? "+" : ""}${item.delta_pct.toFixed(1)}%`, item.delta_pct < 0 ? T.green : T.red)}
                {item.delta_abs != null && chip(`Δ ${item.delta_abs > 0 ? "+" : ""}${sym}${Math.abs(item.delta_abs).toFixed(2)}`, T.text3, true)}
                {chip(fmtDate(item.changed_at), T.text3, true)}
              </>
            )
          })}
        {expandedCard === "Promotions" && competitorInsights &&
          renderInsightPanel("Promotions", competitorInsights.promotions, `${T.amber}40`, item => {
            const d = item.deal_info
            const sym = d?.currency === "EUR" ? "€" : d?.currency === "GBP" ? "£" : "$"
            return (
              <>
                {item.coupon_text && chip(item.coupon_text, T.amber)}
                {d?.deal_badge && chip(d.deal_badge, T.amber)}
                {(d?.deal_type || d?.deal_state) && chip([d?.deal_type, d?.deal_state].filter(Boolean).join(" · "), T.text2, true)}
                {d?.deal_price != null && chip(`Deal ${sym}${d.deal_price.toFixed(2)}`, T.green)}
                {d?.list_price != null && chip(`List ${sym}${d.list_price.toFixed(2)}`, T.text3, true)}
                {d?.savings_percentage != null && chip(`-${d.savings_percentage}%`, T.green)}
                {d?.savings_amount != null && chip(`-${sym}${d.savings_amount.toFixed(2)}`, T.green)}
                {d?.deal_ends_at && chip(`ends ${fmtDate(d.deal_ends_at)}`, T.text3, true)}
                {chip(fmtDate(item.changed_at), T.text3, true)}
              </>
            )
          })}
        {expandedCard === "Availability Changes" && competitorInsights &&
          renderInsightPanel("Availability Changes", competitorInsights.availability_changes, `${T.red}40`, item => {
            const sc = (s: string) => s === "IN_STOCK" ? T.green : T.red
            return (
              <>
                {chip(item.previous_status, sc(item.previous_status))}
                <span style={{ fontSize: 10, color: T.text3, alignSelf: "center" }}>→</span>
                {chip(item.current_status, sc(item.current_status))}
                {chip(fmtDate(item.changed_at), T.text3, true)}
              </>
            )
          })}
        {expandedCard === "Variation Changes" && competitorInsights &&
          renderInsightPanel("Variation Changes", competitorInsights.variation_changes, `${T.purple}40`, item => (
            <>
              {item.previous_variation_count != null && chip(`${item.previous_variation_count} vars`, T.text3, true)}
              {(item.previous_variation_count != null || item.current_variation_count != null) && <span style={{ fontSize: 10, color: T.text3, alignSelf: "center" }}>→</span>}
              {item.current_variation_count != null && chip(`${item.current_variation_count} vars`, T.purple)}
              {chip(fmtDate(item.changed_at), T.text3, true)}
            </>
          ))}
      </div>

      {/* Competitor Alerts */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: T.text3, marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.06em" }}>Competitor Alerts</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 10 }}>
          {[
            { label: "Out of Stock", value: competitorAlerts?.oos_count ?? 0, color: T.red, icon: <AlertTriangle size={13} /> },
            { label: "Price Drops", value: competitorAlerts?.price_drop_count ?? 0, color: T.green, icon: <TrendingDown size={13} /> },
            { label: "Price Increases", value: competitorAlerts?.price_increase_count ?? 0, color: T.blue, icon: <TrendingUp size={13} /> },
            { label: "New Promotions", value: competitorAlerts?.new_promotion_count ?? 0, color: T.amber, icon: <Bell size={13} /> },
            { label: "New Variations", value: competitorAlerts?.new_variation_count ?? 0, color: T.purple, icon: <Package size={13} /> },
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
      </div>

      {/* Highlights + Threats */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginBottom: 20 }}>
        {/* Category Highlights */}
        <div className="card">
          <div style={{ fontSize: 13, fontWeight: 600, color: T.text1, marginBottom: 14 }}>Category Highlights</div>
          {data.category_highlights.length === 0 && (
            <div style={{ textAlign: "center", padding: "24px 0", color: T.text3, fontSize: 12 }}>No category data</div>
          )}
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
          <button className="btn-ghost" style={{ width: "100%", justifyContent: "center", marginTop: 10, fontSize: 12 }} onClick={() => setPage("categories")}>
            View categories <ChevronRight size={13} />
          </button>
        </div>

        {/* Competitor Highlights */}
        <div className="card">
          <div style={{ fontSize: 13, fontWeight: 600, color: T.text1, marginBottom: 14 }}>Competitor Highlights</div>
          {data.competitor_highlights.length === 0 && (
            <div style={{ textAlign: "center", padding: "24px 0", color: T.text3, fontSize: 12 }}>No competitor data</div>
          )}
          {data.competitor_highlights.map(h => (
            <div key={h.tracker_code} style={{ padding: "10px 0", borderBottom: `1px solid ${T.border}` }}>
              <div style={{ fontSize: 12, color: T.text0, fontWeight: 500, marginBottom: 6 }}>{h.tracker_name}</div>
              <div style={{ display: "flex", gap: 12, fontSize: 11 }}>
                <span style={{ color: T.blue }}>💰 {h.price_change_count} price</span>
                <span style={{ color: T.purple }}>📦 {h.availability_change_count} stock</span>
                <span style={{ color: T.teal }}>📝 {h.listing_change_count} listing</span>
              </div>
            </div>
          ))}
          <button className="btn-ghost" style={{ width: "100%", justifyContent: "center", marginTop: 10, fontSize: 12 }} onClick={() => setPage("competitors")}>
            View competitors <ChevronRight size={13} />
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
