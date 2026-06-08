"use client"

import { useState, useEffect } from "react"
import Image from "next/image"
import { Search, Plus, X, AlertCircle, RefreshCw, Star, Zap } from "lucide-react"
import { T } from "../shared/DesignTokens"
import { PageHeader } from "../shared/PageHeader"
import { Badge } from "../shared/Badge"
import { AlertTypeMeta } from "../shared/AlertTypeMeta"
import {
  apiListKeywordTrackers,
  apiGetLatestKeywordSnapshot,
  apiCreateKeywordTracker,
  apiUpdateKeywordTracker,
  apiDeleteKeywordTracker,
  apiGetKeywordInsights,
  apiListEvents,
  ApiError,
} from "../shared/api"
import type {
  KeywordTracker,
  KeywordTrackerCreateRequest,
  KeywordTrackerUpdateRequest,
  CategorySnapshot,
  CategorySnapshotProduct,
  Timeframe,
  TrackerStatus,
  Event,
  EventType,
  KeywordInsights,
} from "../shared/types"

type KpiFilter = "ALL" | "NEW_ENTRANTS" | "RETURNING" | "EXITS" | "ENTER_TOP10" | "EXIT_TOP10"

type TableRow =
  | { kind: "product"; key: string; product: CategorySnapshotProduct }
  | { kind: "event"; key: string; event: Event }

const FILTER_TO_EVENT: Record<Exclude<KpiFilter, "ALL">, EventType> = {
  NEW_ENTRANTS: "NEW_ENTRANT_TOP50",
  RETURNING: "RETURNING_TOP50",
  EXITS: "EXIT_TOP50",
  ENTER_TOP10: "ENTER_TOP10",
  EXIT_TOP10: "EXIT_TOP10",
}

// ── Helpers ──────────────────────────────────────────────────────────────

const formatMoney = (value: number, currency?: string | null): string => {
  const symbol = currency === "EUR" ? "€" : currency === "GBP" ? "£" : "$"
  return `${symbol}${value.toFixed(2)}`
}

const inputStyle: React.CSSProperties = {
  width: "100%", padding: "9px 12px", borderRadius: 8, border: `1px solid ${T.border}`,
  background: T.bg3, color: T.text0, fontSize: 13, fontFamily: T.sans, outline: "none", boxSizing: "border-box" as const,
}
const labelStyle: React.CSSProperties = {
  display: "block", fontSize: 11, fontWeight: 600, color: T.text2,
  marginBottom: 6, letterSpacing: ".04em", textTransform: "uppercase" as const,
}

const MARKETPLACES = [
  { value: "amazon_us", label: "\u{1F1FA}\u{1F1F3} amazon_us" },
  { value: "amazon_de", label: "\u{1F1E9}\u{1F1EA} amazon_de" },
  { value: "amazon_uk", label: "\u{1F1EC}\u{1F1E7} amazon_uk" },
  { value: "amazon_fr", label: "\u{1F1EB}\u{1F1F7} amazon_fr" },
  { value: "amazon_it", label: "\u{1F1EE}\u{1F1F9} amazon_it" },
  { value: "amazon_es", label: "\u{1F1EA}\u{1F1F8} amazon_es" },
  { value: "amazon_ca", label: "\u{1F1E8}\u{1F1E6} amazon_ca" },
  { value: "amazon_jp", label: "\u{1F1EF}\u{1F1F5} amazon_jp" },
]

const rankTrendMeta = (product: CategorySnapshotProduct) => {
  if (product.rank_trend === "NEW") return { color: T.green, label: "New" }
  if (product.rank_trend === "UP") return { color: T.green, label: `+${product.rank_delta}` }
  if (product.rank_trend === "DOWN") return { color: T.red, label: `${product.rank_delta}` }
  if (product.rank_trend === "STABLE") return { color: T.text3, label: "0" }
  return { color: T.text3, label: "—" }
}

const getEventImageUrl = (event: Event): string | null => {
  return event.payload.current?.main_image_url || event.payload.previous?.main_image_url || null
}

const matchesSearch = (search: string, product: CategorySnapshotProduct): boolean => {
  if (!search) return true
  const q = search.toLowerCase()
  return (
    product.title.toLowerCase().includes(q) ||
    product.asin.toLowerCase().includes(q) ||
    product.brand.toLowerCase().includes(q)
  )
}

const matchesEventSearch = (search: string, event: Event): boolean => {
  if (!search) return true
  const q = search.toLowerCase()
  return (
    event.title.toLowerCase().includes(q) ||
    event.asin.toLowerCase().includes(q) ||
    event.summary.toLowerCase().includes(q)
  )
}

// ── Create Keyword Tracker Modal ─────────────────────────────────────────
interface CreateModalProps { onClose: () => void; onCreate: (t: KeywordTracker) => void }

const CreateKeywordTrackerModal = ({ onClose, onCreate }: CreateModalProps) => {
  const [keyword, setKeyword] = useState("")
  const [name, setName] = useState("")
  const [marketplace, setMarketplace] = useState("amazon_us")
  const [hourUtc, setHourUtc] = useState(2)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!keyword.trim()) { setError("Please enter a keyword."); return }
    if (!name.trim()) { setError("Please enter a tracker name."); return }
    const payload: KeywordTrackerCreateRequest = {
      name: name.trim(),
      marketplace,
      scope: { keyword: keyword.trim() },
      schedule: { frequency: "DAILY", hour_utc: hourUtc },
    }
    setSubmitting(true)
    try {
      const tracker = await apiCreateKeywordTracker(payload)
      onCreate(tracker)
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setError("A tracker for this keyword already exists.")
        } else if (err.status === 400 && err.details?.reason) {
          setError(err.details.reason)
        } else {
          setError(err.message || "Failed to create tracker. Please try again.")
        }
      } else {
        setError("Failed to create tracker. Please try again.")
      }
      setSubmitting(false)
    }
  }

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)", zIndex: 100, overflowY: "auto" }}>
      <div style={{ minHeight: "100%", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
        <div className="card" style={{ width: "100%", maxWidth: 560, padding: "24px 28px", position: "relative" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
            <span style={{ fontSize: 16, fontWeight: 700, color: T.text0 }}>New Keyword Tracker</span>
            <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: T.text3, display: "flex" }}><X size={18} /></button>
          </div>
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>Search Keyword</label>
              <div style={{ position: "relative" }}>
                <Search size={13} style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)", color: T.text3, pointerEvents: "none" }} />
                <input type="text" value={keyword} onChange={e => setKeyword(e.target.value)}
                  placeholder="e.g. baby bottle warmer"
                  style={{ ...inputStyle, paddingLeft: 32 }} />
              </div>
            </div>
            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>Tracker Name</label>
              <input type="text" value={name} onChange={e => setName(e.target.value)}
                placeholder="e.g. Baby Bottle Warmers" maxLength={120} style={inputStyle} />
            </div>
            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>Marketplace</label>
              <select value={marketplace} onChange={e => setMarketplace(e.target.value)} style={{ ...inputStyle, cursor: "pointer" }}>
                {MARKETPLACES.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
            </div>
            <div style={{ marginBottom: 20 }}>
              <label style={labelStyle}>Run at (UTC hour)</label>
              <select value={hourUtc} onChange={e => setHourUtc(Number(e.target.value))} style={{ ...inputStyle, cursor: "pointer" }}>
                {Array.from({ length: 24 }, (_, i) => <option key={i} value={i}>{String(i).padStart(2, "0")}:00 UTC</option>)}
              </select>
            </div>
            {error && (
              <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "9px 12px", borderRadius: 8, background: `${T.red}18`, border: `1px solid ${T.red}40`, marginBottom: 14 }}>
                <AlertCircle size={13} style={{ color: T.red, flexShrink: 0 }} />
                <span style={{ fontSize: 12, color: T.red }}>{error}</span>
              </div>
            )}
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button type="button" onClick={onClose} className="btn-ghost">Cancel</button>
              <button type="submit" disabled={submitting} className="btn-primary" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <Plus size={14} /> {submitting ? "Creating..." : "Create Tracker"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

// ── Edit Keyword Tracker Modal ───────────────────────────────────────────
interface EditModalProps { tracker: KeywordTracker; onClose: () => void; onUpdate: (t: KeywordTracker) => void }

const EditKeywordTrackerModal = ({ tracker, onClose, onUpdate }: EditModalProps) => {
  const [name, setName] = useState(tracker.name)
  const [hourUtc, setHourUtc] = useState(tracker.schedule.hour_utc)
  const [status, setStatus] = useState<TrackerStatus>(tracker.status as TrackerStatus)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!name.trim()) { setError("Name is required."); return }
    const payload: KeywordTrackerUpdateRequest = {
      name: name.trim(),
      schedule: { frequency: "DAILY", hour_utc: hourUtc },
      status,
    }
    setSubmitting(true)
    try {
      const updated = await apiUpdateKeywordTracker(tracker.tracker_code, payload)
      onUpdate(updated)
    } catch {
      setError("Failed to update tracker. Please try again.")
      setSubmitting(false)
    }
  }

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)", zIndex: 100, overflowY: "auto" }}>
      <div style={{ minHeight: "100%", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
        <div className="card" style={{ width: "100%", maxWidth: 480, padding: "24px 28px", position: "relative" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
            <span style={{ fontSize: 16, fontWeight: 700, color: T.text0 }}>Edit Keyword Tracker</span>
            <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: T.text3, display: "flex" }}><X size={18} /></button>
          </div>
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>Name</label>
              <input type="text" value={name} onChange={e => setName(e.target.value)} maxLength={120} style={inputStyle} />
            </div>
            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>Run at (UTC hour)</label>
              <select value={hourUtc} onChange={e => setHourUtc(Number(e.target.value))} style={{ ...inputStyle, cursor: "pointer" }}>
                {Array.from({ length: 24 }, (_, i) => <option key={i} value={i}>{String(i).padStart(2, "0")}:00 UTC</option>)}
              </select>
            </div>
            <div style={{ marginBottom: 20 }}>
              <label style={labelStyle}>Status</label>
              <div style={{ display: "flex", gap: 8 }}>
                {(["ACTIVE", "PAUSED", "ARCHIVED"] as TrackerStatus[]).map(s => (
                  <button key={s} type="button" onClick={() => setStatus(s)}
                    style={{ flex: 1, padding: "9px 12px", borderRadius: 8, border: `1px solid ${status === s ? (s === "ACTIVE" ? T.green : s === "PAUSED" ? T.amber : T.text3) : T.border}`, background: status === s ? T.bg4 : T.bg3, color: status === s ? (s === "ACTIVE" ? T.green : s === "PAUSED" ? T.amber : T.text3) : T.text2, fontSize: 12, cursor: "pointer", transition: "all .15s" }}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
            {error && (
              <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "9px 12px", borderRadius: 8, background: `${T.red}18`, border: `1px solid ${T.red}40`, marginBottom: 14 }}>
                <AlertCircle size={13} style={{ color: T.red, flexShrink: 0 }} />
                <span style={{ fontSize: 12, color: T.red }}>{error}</span>
              </div>
            )}
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button type="button" onClick={onClose} className="btn-ghost">Cancel</button>
              <button type="submit" disabled={submitting} className="btn-primary">
                {submitting ? "Saving..." : "Save Changes"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

// ── Main KeywordPage ─────────────────────────────────────────────────────
export const KeywordPage = () => {
  const [trackers, setTrackers] = useState<KeywordTracker[]>([])
  const [selectedCode, setSelectedCode] = useState<string>("")
  const [snapshot, setSnapshot] = useState<CategorySnapshot | null>(null)
  const [search, setSearch] = useState("")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [showEdit, setShowEdit] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const [activeKpiFilter, setActiveKpiFilter] = useState<KpiFilter>("ALL")
  const [events, setEvents] = useState<Event[]>([])
  const [insights, setInsights] = useState<KeywordInsights | null>(null)
  const [insightsTimeframe, setInsightsTimeframe] = useState<Timeframe>("WEEKLY")

  // Load trackers
  useEffect(() => {
    apiListKeywordTrackers()
      .then(res => {
        setTrackers(res.items)
        if (res.items.length > 0) {
          const firstActive = res.items.find(t => t.status === "ACTIVE") ?? res.items[0]
          setSelectedCode(firstActive.tracker_code)
        }
      })
      .catch(() => {
        setTrackers([])
        setError("Failed to load keyword trackers")
      })
      .finally(() => setLoading(false))
  }, [])

  // Load snapshot when tracker changes
  useEffect(() => {
    if (!selectedCode) return
    let cancelled = false
    apiGetLatestKeywordSnapshot(selectedCode)
      .then(snap => { if (!cancelled) { setSnapshot(snap); setLoading(false) } })
      .catch(() => { if (!cancelled) { setSnapshot(null); setLoading(false) } })
    return () => { cancelled = true }
  }, [selectedCode, refreshKey])

  // Load events when filter changes
  useEffect(() => {
    if (!selectedCode || !snapshot?.snapshot_date || activeKpiFilter === "ALL") {
      return
    }
    let cancelled = false
    apiListEvents({
      tracker_type: "KEYWORD",
      tracker_code: selectedCode,
      from_date: snapshot.snapshot_date,
      to_date: snapshot.snapshot_date,
      page_size: 200,
    })
      .then(res => {
        if (cancelled) return
        setEvents(res.items.filter(event => Object.values(FILTER_TO_EVENT).includes(event.event_type)))
      })
      .catch(() => { if (!cancelled) setEvents([]) })
    return () => { cancelled = true }
  }, [selectedCode, snapshot, activeKpiFilter])

  // Load insights
  useEffect(() => {
    apiGetKeywordInsights(insightsTimeframe)
      .then(d => setInsights(d))
      .catch(() => {})
  }, [insightsTimeframe])

  const selectedTracker = trackers.find(t => t.tracker_code === selectedCode)

  const handleCreate = (tracker: KeywordTracker) => {
    setShowCreate(false)
    setTrackers(prev => [...prev, tracker])
    setSelectedCode(tracker.tracker_code)
    setLoading(true)
    setRefreshKey(k => k + 1)
  }

  const handleUpdate = (tracker: KeywordTracker) => {
    setShowEdit(false)
    setTrackers(prev => prev.map(t => t.tracker_code === tracker.tracker_code ? tracker : t))
    setLoading(true)
    setRefreshKey(k => k + 1)
  }

  const handleDelete = async () => {
    if (!selectedCode) return
    if (!window.confirm("Delete this tracker and all its snapshots?")) return
    try {
      await apiDeleteKeywordTracker(selectedCode)
      setTrackers(prev => prev.filter(t => t.tracker_code !== selectedCode))
      setSelectedCode("")
      setSnapshot(null)
    } catch {
      setError("Failed to delete tracker.")
    }
  }

  const products = snapshot?.products ?? []
  const filteredProducts = products.filter(p => matchesSearch(search, p))
  const filteredEvents = events.filter(e => matchesEventSearch(search, e))

  const tableRows: TableRow[] = activeKpiFilter === "ALL"
    ? filteredProducts.map(p => ({ kind: "product", key: p.asin, product: p }))
    : filteredEvents.map(e => ({ kind: "event", key: e.event_code, event: e }))

  // KPI counts
  const newEntrantCount = snapshot?.summary.new_entrant_count ?? 0
  const returningCount = snapshot?.summary.returning_count ?? 0
  const exitCount = snapshot?.summary.exit_count ?? 0
  const enterTop10Count = snapshot?.summary.enter_top10_count ?? 0
  const exitTop10Count = snapshot?.summary.exit_top10_count ?? 0

  const kpiFilters: { key: KpiFilter; label: string; value: number; color: string }[] = [
    { key: "ALL", label: "All Results", value: products.length, color: T.text0 },
    { key: "NEW_ENTRANTS", label: "New Entrants", value: newEntrantCount, color: T.green },
    { key: "RETURNING", label: "Returning", value: returningCount, color: T.purple },
    { key: "EXITS", label: "Exits", value: exitCount, color: T.red },
    { key: "ENTER_TOP10", label: "Enter Top 10", value: enterTop10Count, color: T.amber },
    { key: "EXIT_TOP10", label: "Exit Top 10", value: exitTop10Count, color: T.red },
  ]

  return (
    <div>
      <PageHeader title="Keyword Tracker" sub="Monitor Amazon search results for keywords" />

      {/* Tracker List */}
      <div className="card" style={{ marginBottom: 16, padding: "14px 18px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: trackers.length > 0 ? 12 : 0 }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: T.text2, textTransform: "uppercase", letterSpacing: ".05em" }}>Trackers</span>
          <div style={{ flex: 1 }} />
          <button className="btn-primary" onClick={() => setShowCreate(true)} style={{ fontSize: 12, padding: "6px 12px" }}>
            <Plus size={13} /> New Keyword
          </button>
        </div>
        {trackers.length === 0 && !loading && (
          <div style={{ textAlign: "center", padding: "24px 0", color: T.text3, fontSize: 12 }}>No keyword trackers yet</div>
        )}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {trackers.map(t => {
            const active = t.tracker_code === selectedCode
            return (
              <button key={t.tracker_code} onClick={() => { setLoading(true); setSelectedCode(t.tracker_code); setActiveKpiFilter("ALL") }}
                style={{ padding: "8px 14px", borderRadius: 8, border: `1px solid ${active ? T.amber : T.border}`, background: active ? T.bg4 : T.bg3, color: active ? T.text0 : T.text2, fontSize: 12, cursor: "pointer", display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 3, transition: "all .15s" }}>
                <span style={{ fontWeight: 500 }}>{t.name}</span>
                <span style={{ fontFamily: T.mono, fontSize: 10, color: T.text3 }}>{t.scope.keyword}</span>
                <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                  <span style={{ fontSize: 9, color: t.status === "ACTIVE" ? T.green : T.text3 }}>{t.status}</span>
                  {t.stats.snapshot_count > 0 && <span style={{ fontSize: 9, color: T.text3 }}>{t.stats.snapshot_count} snaps</span>}
                </div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "9px 12px", borderRadius: 8, background: `${T.red}18`, border: `1px solid ${T.red}40`, marginBottom: 14 }}>
          <AlertCircle size={13} style={{ color: T.red, flexShrink: 0 }} />
          <span style={{ fontSize: 12, color: T.red }}>{error}</span>
        </div>
      )}

      {/* No tracker selected */}
      {!selectedCode && trackers.length === 0 && !loading && (
        <div className="card" style={{ textAlign: "center", padding: "48px 0", color: T.text3, fontSize: 13 }}>
          <Search size={28} style={{ marginBottom: 10, opacity: 0.4 }} />
          <div>Create a keyword tracker to monitor Amazon search results</div>
        </div>
      )}

      {selectedCode && (
        <>
          {/* Tracker Header */}
          {selectedTracker && (
            <div className="card" style={{ marginBottom: 16, padding: "14px 18px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: T.text0 }}>{selectedTracker.name}</div>
                    <div style={{ fontSize: 11, color: T.text3, fontFamily: T.mono, marginTop: 2 }}>
                      &quot;{selectedTracker.scope.keyword}&quot; | top {selectedTracker.tracking_config.top_n} | daily @ {String(selectedTracker.schedule.hour_utc).padStart(2, "0")}:00 UTC
                    </div>
                  </div>
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <button className="btn-ghost" onClick={() => setShowEdit(true)} style={{ fontSize: 12 }}>Edit</button>
                  <button className="btn-ghost" onClick={handleDelete} style={{ fontSize: 12, color: T.red }}>Delete</button>
                  <button className="btn-ghost" onClick={() => { setLoading(true); setRefreshKey(k => k + 1) }} style={{ fontSize: 12 }}>
                    <RefreshCw size={13} /> Refresh
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* KPIs */}
          {snapshot && (
            <div className="card" style={{ marginBottom: 16, padding: "14px 18px" }}>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {kpiFilters.map(kpi => {
                  const active = activeKpiFilter === kpi.key
                  return (
                    <button key={kpi.key} onClick={() => setActiveKpiFilter(kpi.key)}
                      style={{ padding: "8px 14px", borderRadius: 8, border: `1px solid ${active ? kpi.color : T.border}`, background: active ? `${kpi.color}18` : T.bg3, color: active ? kpi.color : T.text2, fontSize: 12, cursor: "pointer", display: "flex", alignItems: "center", gap: 6, transition: "all .15s" }}>
                      <span style={{ fontSize: 16, fontWeight: 700, fontFamily: T.mono }}>{kpi.value}</span>
                      {kpi.label}
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {/* Search */}
          <div className="card" style={{ marginBottom: 16, padding: "14px 18px" }}>
            <div style={{ position: "relative" }}>
              <Search size={13} style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)", color: T.text3, pointerEvents: "none" }} />
              <input type="text" value={search} onChange={e => setSearch(e.target.value)}
                placeholder="Search by title, ASIN, or brand..."
                style={{ ...inputStyle, paddingLeft: 32 }} />
            </div>
          </div>

          {/* Results */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div style={{ padding: "14px 18px", borderBottom: `1px solid ${T.border}`, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: T.text1 }}>
                {activeKpiFilter === "ALL" ? `Search Results (${filteredProducts.length})` : `Filtered Events (${filteredEvents.length})`}
              </span>
              {snapshot && (
                <span style={{ fontSize: 10, color: T.text3, fontFamily: T.mono }}>
                  {snapshot.snapshot_date}
                </span>
              )}
            </div>

            {loading ? (
              <div style={{ textAlign: "center", padding: "48px 0", color: T.text3, fontSize: 12 }}>Loading...</div>
            ) : tableRows.length === 0 ? (
              <div style={{ textAlign: "center", padding: "48px 0", color: T.text3, fontSize: 12 }}>
                {search ? "No results match your search" : "No data for this tracker"}
              </div>
            ) : (
              <div>
                {tableRows.slice(0, 50).map(row => {
                  if (row.kind === "event") {
                    const e = row.event
                    const meta = AlertTypeMeta(e.event_type)
                    const img = getEventImageUrl(e)
                    return (
                      <div key={row.key} className="row-hover" style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 18px", borderBottom: `1px solid ${T.border}` }}>
                        {img ? (
                          <Image unoptimized src={img} alt="" width={32} height={32} style={{ objectFit: "contain", borderRadius: 4, background: T.bg3, flexShrink: 0 }}
                            onError={ev => { (ev.target as HTMLImageElement).style.visibility = "hidden" }} />
                        ) : <div style={{ width: 32, height: 32, borderRadius: 4, background: T.bg3, flexShrink: 0 }} />}
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 12, color: T.text0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{e.title}</div>
                          <div style={{ display: "flex", gap: 6, alignItems: "center", marginTop: 2 }}>
                            <span style={{ fontFamily: T.mono, fontSize: 10, color: T.amber }}>{e.asin}</span>
                            {e.payload.current_rank && <span style={{ fontFamily: T.mono, fontSize: 10, color: T.text3 }}>#{e.payload.current_rank}</span>}
                          </div>
                        </div>
                        <div style={{ display: "flex", gap: 6, alignItems: "center", flexShrink: 0 }}>
                          <Badge type={meta.badgeType} text={meta.label} />
                          <Badge type={e.severity === "HIGH" ? "exit" : e.severity === "MEDIUM" ? "top10" : "info"} text={e.severity} />
                        </div>
                      </div>
                    )
                  }
                  // product row
                  const p = row.product
                  const trend = rankTrendMeta(p)
                  return (
                    <div key={row.key} className="row-hover" style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 18px", borderBottom: `1px solid ${T.border}` }}>
                      {p.image_url ? (
                        <a href={p.product_url || `https://www.amazon.com/dp/${p.asin}`} target="_blank" rel="noopener noreferrer" style={{ flexShrink: 0 }}>
                          <Image unoptimized src={p.image_url} alt="" width={32} height={32} style={{ objectFit: "contain", borderRadius: 4, background: T.bg3 }}
                            onError={ev => { (ev.target as HTMLImageElement).style.visibility = "hidden" }} />
                        </a>
                      ) : <div style={{ width: 32, height: 32, borderRadius: 4, background: T.bg3, flexShrink: 0 }} />}
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 12, color: T.text0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.title}</div>
                        <div style={{ display: "flex", gap: 6, alignItems: "center", marginTop: 2 }}>
                          <span style={{ fontFamily: T.mono, fontSize: 10, color: T.amber }}>{p.asin}</span>
                          {p.brand && <span style={{ fontSize: 10, color: T.text3 }}>{p.brand}</span>}
                        </div>
                      </div>
                      <div style={{ display: "flex", gap: 8, alignItems: "center", flexShrink: 0 }}>
                        <div style={{ textAlign: "right" }}>
                          <div style={{ fontFamily: T.mono, fontSize: 11, color: T.text0 }}>
                            {p.rank_position > 0 ? `#${p.rank_position}` : "—"}
                          </div>
                          <div style={{ fontSize: 10, color: trend.color, fontFamily: T.mono }}>{trend.label}</div>
                        </div>
                        {p.price_current > 0 && (
                          <div style={{ fontFamily: T.mono, fontSize: 11, color: T.text0, textAlign: "right", minWidth: 56 }}>
                            {formatMoney(p.price_current, p.currency)}
                          </div>
                        )}
                        <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                          <span style={{ fontSize: 10, color: T.amber }}>{p.rating_value > 0 ? p.rating_value.toFixed(1) : "—"}</span>
                          <span style={{ fontSize: 9, color: T.text3 }}>({p.review_count})</span>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Keyword Insights */}
          <div className="card" style={{ marginBottom: 16, padding: "14px 18px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: T.text1 }}>Keyword Insights</span>
              <select value={insightsTimeframe} onChange={e => setInsightsTimeframe(e.target.value as Timeframe)}
                style={{ padding: "4px 8px", borderRadius: 6, border: `1px solid ${T.border}`, background: T.bg3, color: T.text2, fontSize: 11, cursor: "pointer" }}>
                <option value="DAILY">Daily</option>
                <option value="WEEKLY">Weekly</option>
                <option value="MONTHLY">Monthly</option>
              </select>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
              {[
                { label: "Top 10 Entrants", value: insights?.new_top10_entrants.length ?? 0, color: T.amber, icon: <Star size={13} /> },
                { label: "First-Time", value: insights?.first_time_entrants.length ?? 0, color: T.green, icon: <Zap size={13} /> },
                { label: "Returning", value: insights?.returning_entrants.length ?? 0, color: T.purple, icon: <RefreshCw size={13} /> },
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
        </>
      )}

      {/* Modals */}
      {showCreate && <CreateKeywordTrackerModal onClose={() => setShowCreate(false)} onCreate={handleCreate} />}
      {showEdit && selectedTracker && <EditKeywordTrackerModal tracker={selectedTracker} onClose={() => setShowEdit(false)} onUpdate={handleUpdate} />}
    </div>
  )
}
