"use client"

import { useState, useEffect, useMemo } from "react"
import { Search, TrendingUp, TrendingDown, Star, Zap, RefreshCw, ExternalLink } from "lucide-react"
import { T } from "../shared/DesignTokens"
import { PageHeader } from "../shared/PageHeader"
import { Badge } from "../shared/Badge"
import { apiListCategoryTrackers, apiGetLatestCategorySnapshot } from "../shared/api"
import type { CategoryTracker, CategorySnapshot, CategorySnapshotProduct } from "../shared/types"

export const CategoryPage = () => {
  const [trackers, setTrackers] = useState<CategoryTracker[]>([])
  const [selectedCode, setSelectedCode] = useState<string>("")
  const [snapshot, setSnapshot] = useState<CategorySnapshot | null>(null)
  const [search, setSearch] = useState("")
  const [loading, setLoading] = useState(true)

  // Load trackers
  useEffect(() => {
    apiListCategoryTrackers().then(res => {
      setTrackers(res.items)
      if (res.items.length > 0) setSelectedCode(res.items[0].tracker_code)
      setLoading(false)
    })
  }, [])

  // Load snapshot when tracker changes
  useEffect(() => {
    if (!selectedCode) return
    setLoading(true)
    apiGetLatestCategorySnapshot(selectedCode).then(snap => {
      setSnapshot(snap)
      setLoading(false)
    })
  }, [selectedCode])

  const selectedTracker = trackers.find(t => t.tracker_code === selectedCode)

  const filtered = useMemo(() => {
    if (!snapshot) return []
    if (!search) return snapshot.products
    const s = search.toLowerCase()
    return snapshot.products.filter(p => p.title.toLowerCase().includes(s) || p.asin.toLowerCase().includes(s) || p.brand.toLowerCase().includes(s))
  }, [snapshot, search])

  if (loading && trackers.length === 0) return <div style={{ textAlign: "center", padding: 60, color: T.text3 }}>Loading trackers...</div>

  return (
    <div className="anim-fade">
      <PageHeader title="Category Tracker" sub="Top 50 BSR — Daily snapshots from normalized data" />

      {/* Tracker selector tabs */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        {trackers.map(t => (
          <button key={t.tracker_code} onClick={() => setSelectedCode(t.tracker_code)}
            style={{ padding: "7px 14px", borderRadius: 8, border: `1px solid ${t.tracker_code === selectedCode ? T.amber : T.border}`, background: t.tracker_code === selectedCode ? T.bg4 : T.bg2, color: t.tracker_code === selectedCode ? T.amber : T.text1, fontSize: 13, fontFamily: T.sans, cursor: "pointer", transition: "all .15s", display: "flex", alignItems: "center", gap: 6 }}>
            {t.tracker_code === selectedCode && <span className="dot-live" />}
            {t.name}
            <span style={{ fontSize: 10, fontFamily: T.mono, color: T.text3 }}>({t.status})</span>
          </button>
        ))}
      </div>

      {/* Tracker info card */}
      {selectedTracker && (
        <div className="card" style={{ marginBottom: 16, padding: "14px 18px", borderLeft: `3px solid ${T.amber}` }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                <span style={{ fontSize: 15, fontWeight: 700, color: T.text0 }}>{selectedTracker.name}</span>
                <Badge type="top10" text={selectedTracker.marketplace.toUpperCase()} />
                {selectedTracker.status === "ACTIVE" && <span className="dot-live" />}
              </div>
              <div style={{ display: "flex", gap: 16, marginTop: 6 }}>
                <span style={{ fontSize: 11, color: T.text3, fontFamily: T.mono }}>
                  Node: <strong style={{ color: T.amber }}>{selectedTracker.scope.browse_node_id}</strong>
                </span>
                <span style={{ fontSize: 11, color: T.text3 }}>|</span>
                {selectedTracker.scope.browse_node_url && (
                  <a href={selectedTracker.scope.browse_node_url} target="_blank" rel="noopener noreferrer"
                    style={{ fontSize: 11, color: T.blue, fontFamily: T.mono, textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 3 }}>
                    Browse Node URL <ExternalLink size={9} />
                  </a>
                )}
              </div>
              <div style={{ display: "flex", gap: 16, marginTop: 6, fontSize: 11, color: T.text3, fontFamily: T.mono }}>
                <span>Schedule: {selectedTracker.schedule.frequency} @ {selectedTracker.schedule.hour_utc}:00 UTC</span>
                <span>Top N: {selectedTracker.tracking_config.top_n}</span>
                <span>Top 10 Alerts: {selectedTracker.tracking_config.top10_alert_enabled ? "ON" : "OFF"}</span>
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: 10, color: T.text3, fontFamily: T.mono }}>Last Success: {selectedTracker.stats.last_success_at ? new Date(selectedTracker.stats.last_success_at).toLocaleString() : "—"}</div>
              <div style={{ fontSize: 10, color: T.text3, fontFamily: T.mono, marginTop: 2 }}>Snapshots: {selectedTracker.stats.snapshot_count}</div>
              {selectedTracker.latest_snapshot_summary && (
                <div style={{ fontSize: 10, color: T.text3, fontFamily: T.mono, marginTop: 2 }}>Latest: {selectedTracker.latest_snapshot_summary.snapshot_date}</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Snapshot summary KPIs */}
      {snapshot && (
        <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
          {[
            { label: "Total ASINs", v: snapshot.summary.asin_count, color: T.text0, icon: <TrendingUp size={14} /> },
            { label: "New Entrants", v: snapshot.summary.new_entrant_count, color: T.green, icon: <Zap size={14} /> },
            { label: "Returning", v: snapshot.summary.returning_count, color: "#90EE90", icon: <RefreshCw size={14} /> },
            { label: "Exits", v: snapshot.summary.exit_count, color: T.red, icon: <TrendingDown size={14} /> },
            { label: "Enter Top 10", v: snapshot.summary.enter_top10_count, color: T.amber, icon: <Star size={14} /> },
            { label: "Exit Top 10", v: snapshot.summary.exit_top10_count, color: T.red, icon: <TrendingDown size={14} /> },
          ].map(s => (
            <div key={s.label} className="card" style={{ flex: 1, padding: "10px 14px", display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ width: 30, height: 30, borderRadius: 7, background: `${s.color}18`, display: "flex", alignItems: "center", justifyContent: "center", color: s.color }}>{s.icon}</div>
              <div>
                <span style={{ fontSize: 22, fontWeight: 700, fontFamily: T.mono, color: s.color }}>{s.v}</span>
                <div style={{ fontSize: 10, color: T.text2 }}>{s.label}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Snapshot metadata */}
      {snapshot && (
        <div style={{ display: "flex", gap: 12, marginBottom: 8, fontSize: 11, color: T.text3, fontFamily: T.mono }}>
          <span>Snapshot: {snapshot.snapshot_date}</span>
          <span>Captured: {new Date(snapshot.captured_at).toLocaleString()}</span>
          {snapshot.source_refs?.job_code && <span>Job: {snapshot.source_refs.job_code}</span>}
        </div>
      )}

      {/* Products table */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}`, display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ position: "relative", flex: 1, maxWidth: 280 }}>
            <Search size={13} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: T.text3 }} />
            <input className="input" placeholder="Search ASIN, title, or brand..." value={search} onChange={e => setSearch(e.target.value)} style={{ paddingLeft: 30 }} />
          </div>
          <span style={{ fontSize: 11, color: T.text3, fontFamily: T.mono, marginLeft: "auto" }}>
            {filtered.length} of {snapshot?.products.length || 0} products
          </span>
        </div>

        {loading ? (
          <div style={{ textAlign: "center", padding: 40, color: T.text3 }}>Loading snapshot...</div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${T.border}` }}>
                {["#", "ASIN", "Title", "Brand", "Price", "Rating", "Reviews", "Availability", "Buy Box", "Coupon"].map(h => (
                  <th key={h} style={{ padding: "9px 10px", textAlign: "left", fontSize: 10, fontWeight: 600, color: T.text3, letterSpacing: ".06em", textTransform: "uppercase", fontFamily: T.mono, whiteSpace: "nowrap" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((p: CategorySnapshotProduct) => (
                <tr key={p.asin} className="row-hover" style={{ borderBottom: `1px solid ${T.border}`, background: p.rank_position <= 10 ? `${T.bg3}50` : "transparent" }}>
                  <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 13, fontWeight: p.rank_position <= 10 ? 700 : 400, color: p.rank_position <= 10 ? T.amber : T.text1 }}>
                    {String(p.rank_position).padStart(2, "0")}
                  </td>
                  <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 11, color: T.text3 }}>
                    <a href={p.product_url} target="_blank" rel="noopener noreferrer" style={{ color: T.text3, textDecoration: "none" }}>{p.asin}</a>
                  </td>
                  <td style={{ padding: "9px 10px", fontSize: 12, color: T.text0, maxWidth: 240 }}>
                    <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.title}</div>
                  </td>
                  <td style={{ padding: "9px 10px", fontSize: 11, color: T.text2 }}>{p.brand}</td>
                  <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 12, color: T.text1, whiteSpace: "nowrap" }}>
                    {p.currency === "USD" ? "$" : "€"}{p.price_current.toFixed(2)}
                    {p.price_original && p.price_original > p.price_current && (
                      <span style={{ fontSize: 10, color: T.text3, textDecoration: "line-through", marginLeft: 4 }}>{p.price_original.toFixed(2)}</span>
                    )}
                  </td>
                  <td style={{ padding: "9px 10px", fontSize: 12, color: T.green }}>{p.rating_value}★</td>
                  <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 11, color: T.text2 }}>{p.review_count.toLocaleString()}</td>
                  <td style={{ padding: "9px 10px" }}>
                    <Badge type={p.availability_status === "IN_STOCK" ? "listing" : "stock"} text={p.availability_status === "IN_STOCK" ? "In Stock" : p.availability_status === "OUT_OF_STOCK" ? "OOS" : p.availability_status} />
                  </td>
                  <td style={{ padding: "9px 10px" }}>
                    <Badge type={p.buy_box_status === "HAS_BUY_BOX" ? "listing" : "stock"} text={p.buy_box_status === "HAS_BUY_BOX" ? "Has BB" : "No BB"} />
                  </td>
                  <td style={{ padding: "9px 10px", fontSize: 11, color: T.amber }}>
                    {p.coupon_text || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {!loading && filtered.length === 0 && (
          <div style={{ textAlign: "center", padding: "40px 0", color: T.text3, fontSize: 13 }}>No products match your search</div>
        )}
      </div>
    </div>
  )
}
