"use client"

import { useState, useEffect, useMemo, useReducer, Suspense } from "react"
import { Search, TrendingUp, TrendingDown, Star, Zap, RefreshCw, ExternalLink, Plus, Edit2, X, AlertCircle, Trash2 } from "lucide-react"
import { T } from "../shared/DesignTokens"
import { PageHeader } from "../shared/PageHeader"
import { Badge } from "../shared/Badge"
import {
  apiListKeywordTrackers,
  apiGetLatestKeywordSnapshot,
  apiCreateKeywordTracker,
  apiUpdateKeywordTracker,
  apiDeleteKeywordTracker,
  apiTriggerJob,
  apiListEvents,
  ApiError,
} from "../shared/api"
import type {
  KeywordTracker,
  KeywordTrackerCreateRequest,
  KeywordTrackerUpdateRequest,
  CategorySnapshot,
  CategorySnapshotProduct,
  DealInfo,
  TrackerStatus,
  Event,
  EventType,
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

const extractBrandName = (url: string): string => {
  if (!url) return url
  try {
    let match = url.match(/\/stores\/([^/]+)\//)
    if (match?.[1]) return match[1]
    match = url.match(/\/([^/]+)\/b\//)
    if (match?.[1]) return match[1]
    return url
  } catch {
    return url
  }
}

const parseDealItems = (dealInfo?: DealInfo | null): string[] => {
  if (!dealInfo) return []
  const items: string[] = []
  if (dealInfo.deal_badge) items.push(dealInfo.deal_badge)
  const typeAndState = [dealInfo.deal_type, dealInfo.deal_state].filter(Boolean).join(" • ")
  if (typeAndState) items.push(typeAndState)
  if (dealInfo.deal_price != null) items.push(`Deal: ${formatMoney(dealInfo.deal_price, dealInfo.currency)}`)
  if (dealInfo.list_price != null) items.push(`List: ${formatMoney(dealInfo.list_price, dealInfo.currency)}`)
  if (dealInfo.savings_percentage != null || dealInfo.savings_amount != null) {
    const pct = dealInfo.savings_percentage != null ? `${dealInfo.savings_percentage}%` : null
    const amt = dealInfo.savings_amount != null ? formatMoney(dealInfo.savings_amount, dealInfo.currency) : null
    items.push(`Savings: ${[pct, amt].filter(Boolean).join(" • ")}`)
  }
  return items.length > 0 ? items : ["Deal available"]
}

const parseCouponItems = (couponText?: string | null): string[] => {
  if (!couponText) return []
  return couponText
    .split(/\r?\n|\s*\|\s*|\s*;\s*/)
    .map(item => item.trim())
    .filter(Boolean)
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

const eventToProduct = (event: Event): CategorySnapshotProduct => {
  const prev = event.payload.previous
  const prevRank = event.payload.previous_rank ?? null
  const curRank = event.payload.current_rank ?? null
  const rank = prevRank ?? curRank ?? 0
  const currency = prev?.price_current != null ? (event.marketplace === "amazon_us" ? "USD" : event.marketplace === "amazon_uk" ? "GBP" : "EUR") : "USD"

  let rankDelta: number | null = null
  let rankTrend: CategorySnapshotProduct["rank_trend"] = null
  if (prevRank != null && curRank != null) {
    rankDelta = curRank - prevRank
    if (rankDelta > 0) rankTrend = "DOWN"
    else if (rankDelta < 0) rankTrend = "UP"
    else rankTrend = "STABLE"
  }

  return {
    asin: event.asin,
    rank_position: rank,
    previous_rank_position: prevRank,
    rank_delta: rankDelta,
    rank_trend: rankTrend,
    title: prev?.title || event.title || "",
    brand: extractBrandName(prev?.brand || ""),
    product_url: prev?.price_current != null ? `https://www.${event.marketplace.replace("amazon_", "amazon.")}/dp/${event.asin}` : "",
    price_current: prev?.price_current ?? 0,
    price_original: prev?.price_original ?? null,
    currency,
    rating_value: prev?.rating_value ?? 0,
    review_count: prev?.review_count ?? 0,
    image_url: prev?.main_image_url || "",
    availability_status: prev?.availability_status ?? "UNKNOWN",
    buy_box_status: prev?.buy_box_status ?? "UNKNOWN",
    coupon_text: prev?.coupon_text ?? null,
    deal_info: prev?.deal_info ?? null,
  }
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
                <Plus size={14} /> {submitting ? "Creating…" : "Create Tracker"}
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
            <span style={{ fontSize: 16, fontWeight: 700, color: T.text0 }}>Edit Tracker</span>
            <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: T.text3, display: "flex" }}><X size={18} /></button>
          </div>
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>Name</label>
              <input type="text" value={name} onChange={e => setName(e.target.value)} maxLength={120} style={inputStyle} />
            </div>
            <div style={{ marginBottom: 20 }}>
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
                {submitting ? "Saving…" : "Save Changes"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

// ── Events Reducer ──────────────────────────────────────────────────────
type EventsState = { events: Event[]; loading: boolean; error: string | null }
type EventsAction =
  | { type: "FETCH_START" }
  | { type: "FETCH_OK"; events: Event[] }
  | { type: "FETCH_ERR"; error: string }
  | { type: "RESET" }

function eventsReducer(state: EventsState, action: EventsAction): EventsState {
  switch (action.type) {
    case "FETCH_START": return { ...state, loading: true, error: null }
    case "FETCH_OK": return { events: action.events, loading: false, error: null }
    case "FETCH_ERR": return { events: [], loading: false, error: action.error }
    case "RESET": return { events: [], loading: false, error: null }
  }
}

// ── Main KeywordPage ─────────────────────────────────────────────────────
export const KeywordPageInner = () => {
  const [trackers, setTrackers] = useState<KeywordTracker[]>([])
  const [selectedCode, setSelectedCode] = useState<string>("")
  const [snapshot, setSnapshot] = useState<CategorySnapshot | null>(null)
  const [search, setSearch] = useState("")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [showEdit, setShowEdit] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const [statusFilter, setStatusFilter] = useState<string>("ACTIVE")
  const [activeKpiFilter, setActiveKpiFilter] = useState<KpiFilter>("ALL")
  const [eventsState, dispatchEvents] = useReducer(eventsReducer, { events: [], loading: false, error: null })
  const [justAdded, setJustAdded] = useState<string | null>(null)
  const [openCouponKey, setOpenCouponKey] = useState<string | null>(null)
  const [openDealKey, setOpenDealKey] = useState<string | null>(null)
  const [triggering, setTriggering] = useState(false)

  const handleTriggerJob = async () => {
    if (!selectedCode) return
    setTriggering(true)
    try {
      await apiTriggerJob("KEYWORD", selectedCode)
      setRefreshKey(k => k + 1)
    } catch {
      // ignore – user can retry
    } finally {
      setTriggering(false)
    }
  }

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
      dispatchEvents({ type: "RESET" })
      return
    }
    let cancelled = false
    dispatchEvents({ type: "FETCH_START" })
    apiListEvents({
      tracker_type: "KEYWORD",
      tracker_code: selectedCode,
      from_date: snapshot.snapshot_date,
      to_date: snapshot.snapshot_date,
      page_size: 200,
    })
      .then(res => {
        if (cancelled) return
        dispatchEvents({
          type: "FETCH_OK",
          events: res.items.filter(event => Object.values(FILTER_TO_EVENT).includes(event.event_type)),
        })
      })
      .catch(() => {
        if (cancelled) return
        dispatchEvents({ type: "FETCH_ERR", error: "Failed to load events" })
      })
    return () => { cancelled = true }
  }, [selectedCode, snapshot?.snapshot_date, activeKpiFilter])

  const statusColor = (s?: string) => s === "ACTIVE" ? T.green : s === "PAUSED" ? T.amber : s === "ARCHIVED" ? T.red : T.text3

  const selectedTracker = trackers.find(t => t.tracker_code === selectedCode)

  const products = useMemo(() => snapshot?.products ?? [], [snapshot])

  const filteredProducts = useMemo(() => {
    return products.filter(p => matchesSearch(search, p))
  }, [products, search])

  const allVisibleRows = useMemo<TableRow[]>(() => {
    if (!snapshot) return []
    if (activeKpiFilter === "ALL") {
      return filteredProducts.map(p => ({ kind: "product", key: p.asin, product: p }))
    }

    const eventType = FILTER_TO_EVENT[activeKpiFilter]
    const relevantEvents = eventsState.events.filter(e => e.event_type === eventType)

    if (activeKpiFilter === "EXITS") {
      return relevantEvents
        .filter(e => matchesEventSearch(search, e))
        .map(e => {
          const product = eventToProduct(e)
          return { kind: "product" as const, key: `${product.asin}-exit-${e.snapshot_date}`, product }
        })
    }

    if (activeKpiFilter === "EXIT_TOP10") {
      const productsByAsin = new Map(products.map(p => [p.asin, p]))
      return relevantEvents
        .filter(e => matchesEventSearch(search, e))
        .map(e => {
          const product = productsByAsin.get(e.asin)
          if (product) return { kind: "product" as const, key: `${product.asin}-${product.rank_position}`, product }
          const fallbackProduct = eventToProduct(e)
          return { kind: "product" as const, key: `${fallbackProduct.asin}-exit10-${e.snapshot_date}`, product: fallbackProduct }
        })
    }

    const eventAsins = new Set(relevantEvents.map(e => e.asin))
    return filteredProducts
      .filter(p => eventAsins.has(p.asin))
      .map(p => ({ kind: "product", key: p.asin, product: p }))
  }, [snapshot, activeKpiFilter, filteredProducts, eventsState.events, search, products])

  const totalFilteredCount = useMemo(() => {
    if (!snapshot) return 0
    if (activeKpiFilter === "ALL") return snapshot.products.length
    const eventType = FILTER_TO_EVENT[activeKpiFilter]
    if (activeKpiFilter === "EXITS" || activeKpiFilter === "EXIT_TOP10") {
      return eventsState.events.filter(e => e.event_type === eventType).length
    }
    const eventAsins = new Set(
      eventsState.events.filter(e => e.event_type === eventType).map(e => e.asin)
    )
    return snapshot.products.filter(p => eventAsins.has(p.asin)).length
  }, [snapshot, activeKpiFilter, eventsState.events])

  const handleCreate = (tracker: KeywordTracker) => {
    setShowCreate(false)
    setTrackers(prev => [tracker, ...prev])
    setSelectedCode(tracker.tracker_code)
    setJustAdded(tracker.tracker_code)
    setTimeout(() => setJustAdded(null), 5000)
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

  // KPI counts
  const newEntrantCount = snapshot?.summary.new_entrant_count ?? 0
  const returningCount = snapshot?.summary.returning_count ?? 0
  const exitCount = snapshot?.summary.exit_count ?? 0
  const enterTop10Count = snapshot?.summary.enter_top10_count ?? 0
  const exitTop10Count = snapshot?.summary.exit_top10_count ?? 0

  if (trackers.length === 0) return (
    <>
      {showCreate && (
        <CreateKeywordTrackerModal onClose={() => setShowCreate(false)} onCreate={handleCreate} />
      )}
      <div className="anim-fade">
        <PageHeader title="Keyword Tracker" sub="Monitor Amazon search results for keywords"
          actions={
            <button className="btn-primary" onClick={() => setShowCreate(true)}
              style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <Plus size={14} /> New Tracker
            </button>
          } />
        <div style={{ textAlign: "center", padding: "80px 24px", color: T.text3 }}>
          {loading
            ? <div style={{ fontSize: 13 }}>Loading trackers…</div>
            : <>
                <Search size={40} style={{ margin: "0 auto 16px", opacity: 0.3 }} />
                <div style={{ fontSize: 15, fontWeight: 600, color: T.text1, marginBottom: 6 }}>No keyword trackers yet</div>
                <div style={{ fontSize: 12, color: error ? T.red : T.text3, marginBottom: 24 }}>
                  {error ?? "Create a tracker to start monitoring Amazon search results."}
                </div>
                <button className="btn-primary" onClick={() => setShowCreate(true)}
                  style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12 }}>
                  <Plus size={14} /> New Tracker
                </button>
              </>
          }
        </div>
      </div>
    </>
  )

  return (
    <>
      {showCreate && (
        <CreateKeywordTrackerModal onClose={() => setShowCreate(false)} onCreate={handleCreate} />
      )}
      {showEdit && selectedTracker && (
        <EditKeywordTrackerModal
          tracker={selectedTracker}
          onClose={() => setShowEdit(false)}
          onUpdate={handleUpdate}
        />
      )}
      <div className="anim-fade">
        <PageHeader title="Keyword Tracker" sub="Monitor Amazon search results for keywords"
          actions={
            <div style={{ display: "flex", gap: 8 }}>
              {selectedTracker && (
                <button className="btn-ghost" onClick={() => setShowEdit(true)}
                  style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
                  <Edit2 size={14} /> Edit Tracker
                </button>
              )}
              <button className="btn-primary" onClick={() => setShowCreate(true)}
                style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <Plus size={14} /> New Tracker
              </button>
            </div>
          } />

        {/* Status filter tabs */}
        <div style={{ display: "flex", gap: 8, marginBottom: 12, alignItems: "center", flexWrap: "wrap" }}>
          {(["ACTIVE", "PAUSED", "ARCHIVED"] as const).map(s => {
            const sc = statusColor(s)
            const count = trackers.filter(t => (t.status ?? "ACTIVE") === s).length
            if (count === 0) return null
            return (
              <button key={s} onClick={() => setStatusFilter(s)}
                style={{ padding: "5px 12px", borderRadius: 7, border: `1px solid ${statusFilter === s ? sc : T.border}`, background: statusFilter === s ? `${sc}18` : T.bg2, color: statusFilter === s ? sc : T.text3, fontSize: 11, fontFamily: T.mono, fontWeight: 600, cursor: "pointer", transition: "all .15s" }}>
                {s} <span style={{ opacity: .7 }}>({count})</span>
              </button>
            )
          })}
        </div>

        {/* Tracker selector */}
        <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
          {trackers.filter(t => (t.status ?? "ACTIVE") === statusFilter).map(t => {
            const sc = statusColor(t.status)
            const isSelected = t.tracker_code === selectedCode
            return (
              <button key={t.tracker_code} onClick={() => { setSnapshot(null); setLoading(true); setSelectedCode(t.tracker_code); setRefreshKey(k => k + 1) }}
                style={{ padding: "7px 14px", borderRadius: 8, border: `1px solid ${isSelected ? sc : T.border}`, background: isSelected ? T.bg4 : T.bg2, color: isSelected ? sc : T.text1, fontSize: 13, fontFamily: T.sans, cursor: "pointer", transition: "all .15s", display: "flex", alignItems: "center", gap: 6 }}>
                {isSelected && <span className="dot-live" style={{ background: sc, boxShadow: `0 0 0 3px ${sc}30` }} />}
                {t.name}
              </button>
            )
          })}
        </div>

        {/* Error */}
        {error && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "9px 12px", borderRadius: 8, background: `${T.red}18`, border: `1px solid ${T.red}40`, marginBottom: 14 }}>
            <AlertCircle size={13} style={{ color: T.red, flexShrink: 0 }} />
            <span style={{ fontSize: 12, color: T.red }}>{error}</span>
          </div>
        )}

        {/* Tracker info card */}
        {selectedTracker && (
          <div className="card" style={{ marginBottom: 16, padding: "14px 18px", borderLeft: `3px solid ${T.amber}` }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                  <span style={{ fontSize: 15, fontWeight: 700, color: T.text0 }}>{selectedTracker.name}</span>
                  {selectedTracker.status === "ACTIVE" && <span className="dot-live" />}
                </div>
                <div style={{ display: "flex", gap: 16, marginTop: 6 }}>
                  <span style={{ fontSize: 11, color: T.text3, fontFamily: T.mono }}>
                    Keyword: <strong style={{ color: T.amber }}>&quot;{selectedTracker.scope.keyword}&quot;</strong>
                  </span>
                  {selectedTracker.scope.sort_by && (
                    <>
                      <span style={{ fontSize: 11, color: T.text3 }}>|</span>
                      <span style={{ fontSize: 11, color: T.text3, fontFamily: T.mono }}>Sort: {selectedTracker.scope.sort_by}</span>
                    </>
                  )}
                </div>
                <div style={{ display: "flex", gap: 16, marginTop: 6, fontSize: 11, color: T.text3, fontFamily: T.mono }}>
                  <span>Schedule: {selectedTracker.schedule.frequency} @ {String(selectedTracker.schedule.hour_utc).padStart(2, "0")}:00 UTC</span>
                  <span>Top N: {selectedTracker.tracking_config.top_n}</span>
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: 10, color: T.text3, fontFamily: T.mono }}>Last Success: {selectedTracker.stats.last_success_at ? new Date(selectedTracker.stats.last_success_at).toLocaleString() : "—"}</div>
                <div style={{ fontSize: 10, color: T.text3, fontFamily: T.mono, marginTop: 2 }}>Snapshots: {selectedTracker.stats.snapshot_count}</div>
                {selectedTracker.latest_snapshot_summary && (
                  <div style={{ fontSize: 10, color: T.text3, fontFamily: T.mono, marginTop: 2 }}>Latest: {selectedTracker.latest_snapshot_summary.snapshot_date}</div>
                )}
                <button onClick={handleDelete} style={{ marginTop: 8, padding: "4px 10px", borderRadius: 6, border: `1px solid ${T.red}40`, background: "transparent", color: T.red, fontSize: 11, cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 4, fontFamily: T.sans }}>
                  <Trash2 size={11} /> Delete
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Snapshot summary KPIs */}
        {snapshot && (
          <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
            {[
              { key: "ALL" as const, label: "Total ASINs", v: snapshot.summary.asin_count, color: T.text0, icon: <TrendingUp size={14} /> },
              { key: "NEW_ENTRANTS" as const, label: "New Entrants", v: newEntrantCount, color: T.green, icon: <Zap size={14} /> },
              { key: "RETURNING" as const, label: "Returning", v: returningCount, color: "#90EE90", icon: <RefreshCw size={14} /> },
              { key: "EXITS" as const, label: "Exits", v: exitCount, color: T.red, icon: <TrendingDown size={14} /> },
              { key: "ENTER_TOP10" as const, label: "Enter Top 10", v: enterTop10Count, color: T.amber, icon: <Star size={14} /> },
              { key: "EXIT_TOP10" as const, label: "Exit Top 10", v: exitTop10Count, color: T.red, icon: <TrendingDown size={14} /> },
            ].map(s => (
              <button key={s.label} type="button" className="card" onClick={() => setActiveKpiFilter(s.key)} style={{ flex: 1, padding: "10px 14px", display: "flex", alignItems: "center", gap: 10, cursor: "pointer", textAlign: "left", border: `1px solid ${activeKpiFilter === s.key ? s.color : T.border}`, background: activeKpiFilter === s.key ? `${s.color}10` : undefined }}>
                <div style={{ width: 30, height: 30, borderRadius: 7, background: `${s.color}18`, display: "flex", alignItems: "center", justifyContent: "center", color: s.color }}>{s.icon}</div>
                <div>
                  <span style={{ fontSize: 22, fontWeight: 700, fontFamily: T.mono, color: s.color }}>{s.v}</span>
                  <div style={{ fontSize: 10, color: T.text2 }}>{s.label}</div>
                </div>
              </button>
            ))}
          </div>
        )}

        {/* Snapshot metadata */}
        {snapshot && (
          <div style={{ display: "flex", gap: 12, marginBottom: 8, fontSize: 11, color: T.text3, fontFamily: T.mono, flexWrap: "wrap" }}>
            <span>Snapshot: {snapshot.snapshot_date}</span>
            <span>Captured: {new Date(snapshot.captured_at).toLocaleString()}</span>
            {snapshot.source_refs?.provider && <span>Provider: {snapshot.source_refs.provider}</span>}
            {snapshot.source_refs?.apify_run_id && <span>Run: {snapshot.source_refs.apify_run_id}</span>}
          </div>
        )}

        {/* Events loading/error banner */}
        {eventsState.loading && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 14px", marginBottom: 8, borderRadius: 8, background: `${T.blue}12`, border: `1px solid ${T.blue}30`, fontSize: 12, color: T.blue }}>
            <span className="dot-live" style={{ background: T.blue, animation: "pulse 1.5s infinite" }} />
            Loading events...
          </div>
        )}
        {eventsState.error && !eventsState.loading && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 14px", marginBottom: 8, borderRadius: 8, background: `${T.red}12`, border: `1px solid ${T.red}30`, fontSize: 12, color: T.red }}>
            {eventsState.error}
            <button onClick={() => setActiveKpiFilter(prev => prev)} style={{ marginLeft: "auto", padding: "2px 8px", borderRadius: 4, border: `1px solid ${T.red}40`, background: "transparent", color: T.red, fontSize: 11, cursor: "pointer" }}>Retry</button>
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
              {allVisibleRows.length} of {totalFilteredCount} {activeKpiFilter === "ALL" ? "products" : "matched rows"}
            </span>
          </div>

          {justAdded && (
            <div style={{ background: `${T.blue}15`, border: `1px solid ${T.blue}40`, borderRadius: 8, padding: "12px 14px", margin: "12px 14px", color: T.blue, fontSize: 12 }}>
              Data will be collected and displayed in a few minutes.
            </div>
          )}

          {loading ? (
            <div style={{ textAlign: "center", padding: 40, color: T.text3 }}>Loading snapshot...</div>
          ) : (
            <div style={{ width: "100%", overflowX: "auto" }}>
              <table style={{ width: "100%", minWidth: 1100, borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: `1px solid ${T.border}` }}>
                    {["#", "Change", "Img", "ASIN", "Title", "Brand", "Price", "Rating", "Reviews", "Availability", "Deal", "Coupon"].map(h => (
                      <th key={h} style={{ padding: "9px 10px", textAlign: "left", fontSize: 10, fontWeight: 600, color: T.text3, letterSpacing: ".06em", textTransform: "uppercase", fontFamily: T.mono, whiteSpace: "nowrap" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {allVisibleRows.map(row => {
                    if (row.kind === "event") {
                      const event = row.event
                      const imageUrl = getEventImageUrl(event)
                      const rankLabel = event.payload.current_rank ?? event.payload.previous_rank ?? null
                      const prev = event.payload.previous
                      return (
                        <tr key={row.key} className="row-hover" style={{ borderBottom: `1px solid ${T.border}`, background: `${T.bg3}30` }}>
                          <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 13, color: T.text1 }}>
                            {rankLabel != null ? String(rankLabel).padStart(2, "0") : "--"}
                          </td>
                          <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 11, color: T.amber }}>
                            {event.event_type.replaceAll("_", " ")}
                          </td>
                          <td style={{ padding: "6px 10px" }}>
                            <div style={{ width: 36, height: 36, borderRadius: 6, background: T.bg3, border: `1px solid ${T.border}`, overflow: "hidden", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
                              {imageUrl ? (
                                // eslint-disable-next-line @next/next/no-img-element
                                <img src={imageUrl} alt={event.asin} style={{ width: "100%", height: "100%", objectFit: "cover" }} onError={e => { (e.target as HTMLImageElement).style.display = "none" }} />
                              ) : (
                                <span style={{ fontSize: 10, color: T.text3, fontFamily: T.mono }}>N/A</span>
                              )}
                            </div>
                          </td>
                          <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 11, color: T.amber }}>{event.asin}</td>
                          <td style={{ padding: "9px 10px", fontSize: 12, color: T.text0, maxWidth: 240 }}>
                            <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{prev?.title || event.title}</div>
                          </td>
                          <td style={{ padding: "9px 10px", fontSize: 11, color: T.text2, width: 90, maxWidth: 90 }}>
                            {prev?.brand ? (
                              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "inline-block", width: "100%" }}>{extractBrandName(prev.brand)}</span>
                            ) : <span style={{ color: T.text3 }}>—</span>}
                          </td>
                          <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 12, color: T.text1, whiteSpace: "nowrap" }}>
                            {prev?.price_current != null && prev.price_current > 0 ? (
                              <>
                                {event.marketplace === "amazon_us" ? "$" : event.marketplace === "amazon_uk" ? "£" : "€"}{prev.price_current.toFixed(2)}
                                {prev.price_original != null && prev.price_original > prev.price_current && (
                                  <span style={{ fontSize: 10, color: T.text3, textDecoration: "line-through", marginLeft: 4 }}>
                                    {event.marketplace === "amazon_us" ? "$" : event.marketplace === "amazon_uk" ? "£" : "€"}{prev.price_original.toFixed(2)}
                                  </span>
                                )}
                              </>
                            ) : <span style={{ color: T.text3 }}>—</span>}
                          </td>
                          <td style={{ padding: "9px 10px", fontSize: 12, color: T.text3 }}>—</td>
                          <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 11, color: T.text3 }}>—</td>
                          <td style={{ padding: "9px 10px" }}><Badge type="info" text="—" /></td>
                          <td style={{ padding: "9px 10px" }}><Badge type="info" text="—" /></td>
                          <td style={{ padding: "9px 10px", fontSize: 11, color: T.text3 }}>—</td>
                          <td style={{ padding: "9px 10px", fontSize: 11, color: T.text3 }}>—</td>
                        </tr>
                      )
                    }

                    const p = row.product
                    const isExitFilter = activeKpiFilter === "EXITS"
                    return (
                      <tr key={row.key} className="row-hover" style={{ borderBottom: `1px solid ${T.border}`, background: !isExitFilter && p.rank_position <= 10 ? `${T.bg3}50` : "transparent" }}>
                        <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 13, fontWeight: !isExitFilter && p.rank_position <= 10 ? 700 : 400, color: !isExitFilter && p.rank_position <= 10 ? T.amber : T.text1 }}>
                          {isExitFilter ? "—" : String(p.rank_position).padStart(2, "0")}
                        </td>
                        <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 11, whiteSpace: "nowrap" }}>
                          {isExitFilter ? (
                            <span style={{ display: "inline-flex", alignItems: "center", gap: 4, color: T.text3, fontStyle: "italic" }}>
                              Historical
                            </span>
                          ) : (() => {
                            const meta = rankTrendMeta(p)
                            return (
                              <span title={p.comparison_snapshot_date ? `Previous: ${p.previous_rank_position ?? "not ranked"} on ${p.comparison_snapshot_date}` : "No comparison snapshot"}
                                style={{ display: "inline-flex", alignItems: "center", gap: 4, color: meta.color, fontWeight: p.rank_trend && p.rank_trend !== "STABLE" ? 700 : 500 }}>
                                {p.rank_trend === "UP" && <TrendingUp size={12} />}
                                {p.rank_trend === "DOWN" && <TrendingDown size={12} />}
                                {meta.label}
                              </span>
                            )
                          })()}
                        </td>
                        <td style={{ padding: "6px 10px" }}>
                          <div style={{ width: 36, height: 36, borderRadius: 6, background: T.bg3, border: `1px solid ${T.border}`, overflow: "hidden", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img src={p.image_url} alt={p.asin} style={{ width: "100%", height: "100%", objectFit: "cover" }} onError={e => { (e.target as HTMLImageElement).style.display = "none" }} />
                          </div>
                        </td>
                        <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 11 }}>
                          <a href={p.product_url || `https://www.amazon.com/dp/${p.asin}`} target="_blank" rel="noopener noreferrer" style={{ color: T.blue, textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 3 }}>
                            {p.asin}<ExternalLink size={9} />
                          </a>
                        </td>
                        <td style={{ padding: "9px 10px", fontSize: 12, color: T.text0, maxWidth: 240 }}>
                          <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.title}</div>
                        </td>
                        <td style={{ padding: "9px 10px", fontSize: 11, color: T.text2, width: 90, maxWidth: 90 }}>
                          {p.brand ? (
                            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "inline-block", width: "100%" }}>{extractBrandName(p.brand)}</span>
                          ) : <span style={{ color: T.text3 }}>—</span>}
                        </td>
                        <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 12, color: T.text1, whiteSpace: "nowrap" }}>
                          {p.price_current > 0 ? (
                            <>
                              {p.currency === "USD" ? "$" : p.currency === "GBP" ? "£" : "€"}{p.price_current.toFixed(2)}
                              {p.price_original && p.price_original > p.price_current && (
                                <span style={{ fontSize: 10, color: T.text3, textDecoration: "line-through", marginLeft: 4 }}>
                                  {p.currency === "USD" ? "$" : p.currency === "GBP" ? "£" : "€"}{p.price_original.toFixed(2)}
                                </span>
                              )}
                            </>
                          ) : <span style={{ color: T.text3 }}>—</span>}
                        </td>
                        <td style={{ padding: "9px 10px", fontSize: 12, color: T.green }}>
                          {p.rating_value > 0 ? `${p.rating_value}★` : <span style={{ color: T.text3 }}>—</span>}
                        </td>
                        <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 11, color: T.text2 }}>
                          {p.review_count > 0 ? p.review_count.toLocaleString() : <span style={{ color: T.text3 }}>—</span>}
                        </td>
                        <td style={{ padding: "9px 10px" }}>
                          <Badge type={p.availability_status === "IN_STOCK" ? "listing" : "stock"} text={p.availability_status === "IN_STOCK" ? "In Stock" : p.availability_status === "OUT_OF_STOCK" ? "OOS" : p.availability_status} />
                        </td>
                        <td style={{ padding: "9px 10px", fontSize: 11, color: T.blue }}>
                          {(() => {
                            const dealItems = parseDealItems(p.deal_info)
                            if (dealItems.length === 0) return "—"
                            const dealKey = `${p.asin}-${p.rank_position}`
                            const isOpen = openDealKey === dealKey
                            return (
                              <div style={{ minWidth: 160 }}>
                                <button type="button" onClick={() => setOpenDealKey(prev => prev === dealKey ? null : dealKey)}
                                  style={{ padding: "4px 8px", borderRadius: 6, border: `1px solid ${T.blue}`, background: `${T.blue}16`, color: T.blue, fontSize: 10, fontFamily: T.mono, fontWeight: 600, cursor: "pointer" }}>
                                  {isOpen ? "Hide" : "View"} Deal
                                </button>
                                {isOpen && (
                                  <div style={{ marginTop: 6, padding: "6px 8px", background: T.bg3, border: `1px solid ${T.border}`, borderRadius: 6, color: T.text1, lineHeight: 1.4 }}>
                                    {dealItems.map((deal, idx) => (
                                      <div key={`${deal}-${idx}`} style={{ marginBottom: idx < dealItems.length - 1 ? 4 : 0 }}>• {deal}</div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            )
                          })()}
                        </td>
                        <td style={{ padding: "9px 10px", fontSize: 11, color: T.amber }}>
                          {(() => {
                            const couponItems = parseCouponItems(p.coupon_text)
                            if (couponItems.length === 0) return "—"
                            const couponKey = `${p.asin}-${p.rank_position}`
                            const isOpen = openCouponKey === couponKey
                            return (
                              <div style={{ minWidth: 160 }}>
                                <button type="button" onClick={() => setOpenCouponKey(prev => prev === couponKey ? null : couponKey)}
                                  style={{ padding: "4px 8px", borderRadius: 6, border: `1px solid ${T.amberD}`, background: `${T.amber}14`, color: T.amber, fontSize: 10, fontFamily: T.mono, fontWeight: 600, cursor: "pointer" }}>
                                  {isOpen ? "Hide" : "View"} {couponItems.length} Coupon{couponItems.length > 1 ? "s" : ""}
                                </button>
                                {isOpen && (
                                  <div style={{ marginTop: 6, padding: "6px 8px", background: T.bg3, border: `1px solid ${T.border}`, borderRadius: 6, color: T.text1, lineHeight: 1.4 }}>
                                    {couponItems.map((coupon, idx) => (
                                      <div key={`${coupon}-${idx}`} style={{ marginBottom: idx < couponItems.length - 1 ? 4 : 0 }}>• {coupon}</div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            )
                          })()}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}

          {!loading && !snapshot && (
            <div style={{ textAlign: "center", padding: "48px 0", color: T.text3, fontSize: 13 }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>🔍</div>
              <div style={{ fontWeight: 600, color: T.text2, marginBottom: 6 }}>No snapshot yet</div>
              <div style={{ fontSize: 12, marginBottom: 16 }}>This tracker hasn&apos;t run yet.</div>
              <button
                type="button"
                disabled={triggering}
                onClick={handleTriggerJob}
                style={{
                  padding: "8px 20px", borderRadius: 8, border: `1px solid ${T.blue}`,
                  background: triggering ? `${T.blue}60` : T.blue, color: "#fff",
                  fontSize: 13, fontWeight: 600, cursor: triggering ? "wait" : "pointer",
                  fontFamily: T.sans, display: "inline-flex", alignItems: "center", gap: 6,
                }}
              >
                <Zap size={14} />
                {triggering ? "Triggering..." : "Trigger Now"}
              </button>
            </div>
          )}
          {!loading && snapshot && allVisibleRows.length === 0 && (
            <div style={{ textAlign: "center", padding: "40px 0", color: T.text3, fontSize: 13 }}>No products match your search</div>
          )}
        </div>
      </div>
    </>
  )
}

export const KeywordPage = () => (
  <Suspense fallback={<div style={{ textAlign: "center", padding: 40, color: T.text3 }}>Loading...</div>}>
    <KeywordPageInner />
  </Suspense>
)
