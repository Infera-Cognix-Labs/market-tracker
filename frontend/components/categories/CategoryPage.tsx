"use client"

import { useState, useEffect, useMemo, useReducer, Suspense } from "react"
import { Search, TrendingUp, TrendingDown, Star, Zap, RefreshCw, ExternalLink, Plus, Edit2, X, Trash2, CheckCircle, AlertCircle, Info } from "lucide-react"
import { T } from "../shared/DesignTokens"
import { PageHeader } from "../shared/PageHeader"
import { Badge } from "../shared/Badge"
import { Dropdown } from "../shared/Dropdown"
import { ConfirmDialog } from "../shared/ConfirmDialog"
import { apiListCategoryTrackers, apiGetLatestCategorySnapshot, apiCreateCategoryTracker, apiUpdateCategoryTracker, apiDeleteCategoryTracker, apiTriggerJob, apiListEvents, ApiError } from "../shared/api"
import type { CategoryTracker, CategorySnapshot, CategorySnapshotProduct, CategoryTrackerCreateRequest, CategoryTrackerUpdateRequest, Timeframe, TrackerStatus, DealInfo, Event, EventType } from "../shared/types"

type CategoryKpiFilter = "ALL" | "NEW_ENTRANTS" | "RETURNING" | "EXITS" | "ENTER_TOP10" | "EXIT_TOP10"

type CategoryTableRow =
  | { kind: "product"; key: string; product: CategorySnapshotProduct }
  | { kind: "event"; key: string; event: Event }

const CATEGORY_FILTER_TO_EVENT: Record<Exclude<CategoryKpiFilter, "ALL">, EventType> = {
  NEW_ENTRANTS: "NEW_ENTRANT_TOP50",
  RETURNING: "RETURNING_TOP50",
  EXITS: "EXIT_TOP50",
  ENTER_TOP10: "ENTER_TOP10",
  EXIT_TOP10: "EXIT_TOP10",
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function parseBestsellerUrl(input: string): string | null {
  const trimmed = input.trim()
  if (!trimmed.startsWith("http")) return null
  try {
    const url = new URL(trimmed)
    if (url.hostname.includes("amazon.") && (trimmed.includes("/zgbs/") || trimmed.includes("Best-Sellers") || trimmed.includes("best-sellers"))) {
      return trimmed
    }
    return null
  } catch {
    return null
  }
}

const extractBrandName = (url: string): string => {
  if (!url) return url;
  try {
    // Try pattern 1: /stores/BrandName/
    let match = url.match(/\/stores\/([^/]+)\//);
    if (match?.[1]) return match[1];
    
    // Try pattern 2: /BrandName/b/ (Amazon store link)
    match = url.match(/\/([^/]+)\/b\//);
    if (match?.[1]) return match[1];
    
    // Return original if no pattern matches
    return url;
  } catch {
    return url;
  }
};

const parseCouponItems = (couponText?: string | null): string[] => {
  if (!couponText) return []
  return couponText
    .split(/\r?\n|\s*\|\s*|\s*;\s*/)
    .map(item => item.trim())
    .filter(Boolean)
}

const formatMoney = (value: number, currency?: string | null): string => {
  const symbol = currency === "EUR" ? "€" : currency === "GBP" ? "£" : "$"
  return `${symbol}${value.toFixed(2)}`
}

const parseDealItems = (dealInfo?: DealInfo | null): string[] => {
  if (!dealInfo) return []
  const items: string[] = []

  if (dealInfo.deal_badge) items.push(dealInfo.deal_badge)

  const typeAndState = [dealInfo.deal_type, dealInfo.deal_state].filter(Boolean).join(" • ")
  if (typeAndState) items.push(typeAndState)

  if (dealInfo.deal_price != null) {
    items.push(`Deal: ${formatMoney(dealInfo.deal_price, dealInfo.currency)}`)
  }
  if (dealInfo.list_price != null) {
    items.push(`List: ${formatMoney(dealInfo.list_price, dealInfo.currency)}`)
  }
  if (dealInfo.savings_percentage != null || dealInfo.savings_amount != null) {
    const pct = dealInfo.savings_percentage != null ? `${dealInfo.savings_percentage}%` : null
    const amt = dealInfo.savings_amount != null ? formatMoney(dealInfo.savings_amount, dealInfo.currency) : null
    items.push(`Savings: ${[pct, amt].filter(Boolean).join(" • ")}`)
  }

  return items.length > 0 ? items : ["Deal available"]
}

const MARKETPLACE_LABELS: Record<string, string> = {
  amazon_us: "US", amazon_de: "Germany", amazon_uk: "UK", amazon_fr: "France",
  amazon_it: "Italy", amazon_es: "Spain", amazon_ca: "Canada", amazon_jp: "Japan",
}
const marketplaceLabel = (mp: string) => MARKETPLACE_LABELS[mp] ?? mp.replace("amazon_", "").toUpperCase()

const MARKETPLACES = [
  { value: "amazon_us", label: "🇺🇸 amazon_us" },
  { value: "amazon_de", label: "🇩🇪 amazon_de" },
  { value: "amazon_uk", label: "🇬🇧 amazon_uk" },
  { value: "amazon_fr", label: "🇫🇷 amazon_fr" },
  { value: "amazon_it", label: "🇮🇹 amazon_it" },
  { value: "amazon_es", label: "🇪🇸 amazon_es" },
  { value: "amazon_ca", label: "🇨🇦 amazon_ca" },
  { value: "amazon_jp", label: "🇯🇵 amazon_jp" },
]

const inputStyle: React.CSSProperties = { width: "100%", padding: "9px 12px", borderRadius: 8, border: `1px solid ${T.border}`, background: T.bg3, color: T.text0, fontSize: 13, fontFamily: T.sans, outline: "none", boxSizing: "border-box" as const }
const labelStyle: React.CSSProperties = { display: "block", fontSize: 11, fontWeight: 600, color: T.text2, marginBottom: 6, letterSpacing: ".04em", textTransform: "uppercase" as const }

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

const matchesCategorySearch = (search: string, product: CategorySnapshotProduct): boolean => {
  if (!search) return true
  const normalized = search.toLowerCase()
  return (
    product.title.toLowerCase().includes(normalized) ||
    product.asin.toLowerCase().includes(normalized) ||
    product.brand.toLowerCase().includes(normalized)
  )
}

const matchesCategoryEventSearch = (search: string, event: Event): boolean => {
  if (!search) return true
  const normalized = search.toLowerCase()
  return (
    event.title.toLowerCase().includes(normalized) ||
    event.asin.toLowerCase().includes(normalized) ||
    event.summary.toLowerCase().includes(normalized)
  )
}

// ── Create Category Tracker Modal ─────────────────────────────────────────────
interface CreateModalProps { onClose: () => void; onCreate: (t: CategoryTracker) => void }

const HOURS = Array.from({ length: 24 }, (_, i) => ({ value: i, label: `${String(i).padStart(2, "0")}:00 UTC` }))

const CreateCategoryTrackerModal = ({ onClose, onCreate }: CreateModalProps) => {
  const [urlInput, setUrlInput] = useState("")
  const [name, setName] = useState("")
  const [marketplace, setMarketplace] = useState("amazon_us")
  const [top10Alert, setTop10Alert] = useState(true)
  const [hourUtc, setHourUtc] = useState(2)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const parsedUrl = parseBestsellerUrl(urlInput)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!urlInput.trim()) { setError("Please enter a Best-sellers category URL."); return }
    if (!parsedUrl) { setError("Please enter a valid Amazon Best-sellers URL (e.g. https://www.amazon.com/Best-Sellers/zgbs/...)"); return }
    if (!name.trim()) { setError("Please enter a tracker name."); return }
    const scope = { browse_node_url: parsedUrl }
    const payload: CategoryTrackerCreateRequest = {
      name: name.trim(), marketplace, scope,
      tracking_config: { top10_alert_enabled: top10Alert },
      schedule: { frequency: "DAILY", hour_utc: hourUtc },
    }
    setSubmitting(true)
    try {
      const tracker = await apiCreateCategoryTracker(payload)
      onCreate(tracker)
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setError("A tracker for this marketplace and URL already exists.")
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
            <span style={{ fontSize: 16, fontWeight: 700, color: T.text0 }}>New Category Tracker</span>
            <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: T.text3, display: "flex" }}><X size={18} /></button>
          </div>
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>Best-sellers Category URL</label>
              <div style={{ position: "relative" }}>
                <Search size={13} style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)", color: T.text3, pointerEvents: "none" }} />
                <input type="text" value={urlInput} onChange={e => setUrlInput(e.target.value)}
                  placeholder="e.g. https://www.amazon.com/Best-Sellers/zgbs/electronics/"
                  style={{ ...inputStyle, paddingLeft: 32 }} />
              </div>
              {urlInput.trim() && (
                <div style={{ marginTop: 5, display: "flex", alignItems: "center", gap: 6 }}>
                  {parsedUrl
                    ? <><CheckCircle size={12} style={{ color: T.green }} /><span style={{ fontSize: 11, color: T.green }}>Valid Best-sellers URL</span></>
                    : <><AlertCircle size={12} style={{ color: T.red }} /><span style={{ fontSize: 11, color: T.red }}>Please enter a valid Amazon Best-sellers URL</span></>
                  }
                  {parsedUrl && (
                    <a href={parsedUrl} target="_blank" rel="noopener noreferrer"
                      style={{ fontSize: 11, color: T.blue, marginLeft: 8, display: "inline-flex", alignItems: "center", gap: 3, textDecoration: "none" }}>
                      Preview <ExternalLink size={10} />
                    </a>
                  )}
                </div>
              )}
            </div>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>Tracker Name</label>
            <input type="text" value={name} onChange={e => setName(e.target.value)}
              placeholder="e.g. Baby Bottle Warmers - US" maxLength={120} style={inputStyle} />
          </div>
          <div style={{ marginBottom: 16 }}>
            <Dropdown label="Marketplace" value={marketplace} onChange={v => setMarketplace(v as string)} options={MARKETPLACES} />
          </div>
          <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
            <div style={{ flex: 1 }}>
              <Dropdown label="Run at (UTC hour)" value={hourUtc} onChange={v => setHourUtc(Number(v))} options={HOURS} />
            </div>
            <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "flex-end" }}>
              <label style={labelStyle}>Top 10 Alerts</label>
              <button type="button" onClick={() => setTop10Alert(v => !v)}
                style={{ padding: "9px 12px", borderRadius: 8, border: `1px solid ${top10Alert ? T.amber : T.border}`, background: top10Alert ? T.bg4 : T.bg3, color: top10Alert ? T.amber : T.text2, fontSize: 13, cursor: "pointer", display: "flex", alignItems: "center", gap: 8, transition: "all .15s" }}>
                <span style={{ width: 12, height: 12, borderRadius: "50%", background: top10Alert ? T.amber : T.text3, display: "inline-block", flexShrink: 0 }} />
                {top10Alert ? "Enabled" : "Disabled"}
              </button>
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

// ── Edit Category Tracker Modal ───────────────────────────────────────────────
interface EditModalProps { tracker: CategoryTracker; onClose: () => void; onUpdate: (t: CategoryTracker) => void; onDelete: (trackerCode: string) => void }

const EditCategoryTrackerModal = ({ tracker, onClose, onUpdate, onDelete }: EditModalProps) => {
  const [name, setName] = useState(tracker.name)
  const [top10Alert, setTop10Alert] = useState(tracker.tracking_config.top10_alert_enabled)
  const [hourUtc, setHourUtc] = useState(tracker.schedule.hour_utc)
  const [status, setStatus] = useState<TrackerStatus>(tracker.status as TrackerStatus)
  const [submitting, setSubmitting] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!name.trim()) { setError("Name is required."); return }
    const payload: CategoryTrackerUpdateRequest = {
      name: name.trim(),
      tracking_config: { top10_alert_enabled: top10Alert },
      schedule: { frequency: "DAILY", hour_utc: hourUtc },
      status,
    }
    setSubmitting(true)
    try {
      const updated = await apiUpdateCategoryTracker(tracker.tracker_code, payload)
      onUpdate(updated)
    } catch {
      setError("Failed to update tracker. Please try again.")
      setSubmitting(false)
    }
  }

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await apiDeleteCategoryTracker(tracker.tracker_code)
      onDelete(tracker.tracker_code)
    } catch {
      setError("Failed to delete tracker.")
      setDeleting(false)
      setShowConfirm(false)
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
          <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
            <div style={{ flex: 1 }}>
              <Dropdown label="Run at (UTC hour)" value={hourUtc} onChange={v => setHourUtc(Number(v))} options={HOURS} />
            </div>
            <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "flex-end" }}>
              <label style={labelStyle}>Top 10 Alerts</label>
              <button type="button" onClick={() => setTop10Alert(v => !v)}
                style={{ padding: "9px 12px", borderRadius: 8, border: `1px solid ${top10Alert ? T.amber : T.border}`, background: top10Alert ? T.bg4 : T.bg3, color: top10Alert ? T.amber : T.text2, fontSize: 13, cursor: "pointer", display: "flex", alignItems: "center", gap: 8, transition: "all .15s" }}>
                <span style={{ width: 12, height: 12, borderRadius: "50%", background: top10Alert ? T.amber : T.text3, display: "inline-block", flexShrink: 0 }} />
                {top10Alert ? "Enabled" : "Disabled"}
              </button>
            </div>
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
          <div style={{ display: "flex", gap: 10, justifyContent: "space-between" }}>
            <button type="button" onClick={() => setShowConfirm(true)}
              style={{ padding: "9px 14px", borderRadius: 8, border: `1px solid ${T.red}40`, background: "transparent", color: T.red, fontSize: 12, cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 4, fontFamily: T.sans }}>
              <Trash2 size={12} /> Delete
            </button>
            <div style={{ display: "flex", gap: 10 }}>
              <button type="button" onClick={onClose} className="btn-ghost">Cancel</button>
              <button type="submit" disabled={submitting} className="btn-primary">
                {submitting ? "Saving…" : "Save Changes"}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
    <ConfirmDialog
      open={showConfirm}
      title="Delete Tracker"
      message={<>Delete "<b>{tracker.name}</b>" and all its snapshots? This action cannot be undone.</>}
      confirmLabel="Delete"
      loading={deleting}
      onConfirm={handleDelete}
      onCancel={() => setShowConfirm(false)}
    />
    </div>
  )
}

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

export const CategoryPageInner = () => {
  const [trackers, setTrackers] = useState<CategoryTracker[]>([])
  const [selectedCode, setSelectedCode] = useState<string>("")
  const [snapshot, setSnapshot] = useState<CategorySnapshot | null>(null)
  const [search, setSearch] = useState("")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [showEdit, setShowEdit] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const [statusFilter, setStatusFilter] = useState<string>("ACTIVE")
  const [rankTimeframe, setRankTimeframe] = useState<Timeframe>("WEEKLY")
  const [openCouponKey, setOpenCouponKey] = useState<string | null>(null)
  const [openDealKey, setOpenDealKey] = useState<string | null>(null)
  const [activeKpiFilter, setActiveKpiFilter] = useState<CategoryKpiFilter>("ALL")
  const [eventsState, dispatchEvents] = useReducer(eventsReducer, { events: [], loading: false, error: null })
  const [justAdded, setJustAdded] = useState<string | null>(null)
  const [triggering, setTriggering] = useState(false)
  const [showMetaDetail, setShowMetaDetail] = useState(false)

  const handleTriggerJob = async () => {
    if (!selectedCode) return
    setTriggering(true)
    try {
      await apiTriggerJob("CATEGORY", selectedCode)
      setRefreshKey(k => k + 1)
    } catch {
      // ignore
    } finally {
      setTriggering(false)
    }
  }

  // Load trackers
  useEffect(() => {
    apiListCategoryTrackers()
      .then(res => {
        setTrackers(res.items)
        if (res.items.length > 0) {
          const firstActive = res.items.find(t => t.status === "ACTIVE") ?? res.items[0]
          setSelectedCode(firstActive.tracker_code)
        }
      })
      .catch(() => {
        setTrackers([])
        setError("Failed to load category trackers")
      })
      .finally(() => setLoading(false))
  }, [])

  // Load snapshot when tracker changes
  useEffect(() => {
    if (!selectedCode) return
    let cancelled = false
    apiGetLatestCategorySnapshot(selectedCode, rankTimeframe)
      .then(snap => { if (!cancelled) { setSnapshot(snap); setLoading(false) } })
      .catch(() => { if (!cancelled) { setSnapshot(null); setLoading(false) } })
    return () => { cancelled = true }
  }, [selectedCode, rankTimeframe, refreshKey])

  // Reset events when filter changes to ALL — handled by events useEffect returning early

  useEffect(() => {
    if (!selectedCode || !snapshot?.snapshot_date || activeKpiFilter === "ALL") {
      dispatchEvents({ type: "RESET" })
      return
    }
    let cancelled = false
    dispatchEvents({ type: "FETCH_START" })
    apiListEvents({
      tracker_type: "CATEGORY",
      tracker_code: selectedCode,
      from_date: snapshot.snapshot_date,
      to_date: snapshot.snapshot_date,
      page_size: 200,
    })
      .then(res => {
        if (cancelled) return
        dispatchEvents({
          type: "FETCH_OK",
          events: res.items.filter(event => Object.values(CATEGORY_FILTER_TO_EVENT).includes(event.event_type)),
        })
      })
      .catch(() => {
        if (cancelled) return
        dispatchEvents({ type: "FETCH_ERR", error: "Failed to load events" })
      })

    return () => {
      cancelled = true
    }
  }, [selectedCode, snapshot?.snapshot_date, activeKpiFilter])

  const statusColor = (s?: string) => s === "ACTIVE" ? T.green : s === "PAUSED" ? T.amber : s === "ARCHIVED" ? T.red : T.text3

  const selectedTracker = trackers.find(t => t.tracker_code === selectedCode)

  const filteredProducts = useMemo(() => {
    if (!snapshot) return []
    return snapshot.products.filter(product => matchesCategorySearch(search, product))
  }, [snapshot, search])

  const allVisibleRows = useMemo<CategoryTableRow[]>(() => {
    if (!snapshot) return []
    if (activeKpiFilter === "ALL") {
      return filteredProducts.map(product => ({
        kind: "product",
        key: `${product.asin}-${product.rank_position}`,
        product,
      }))
    }

    const eventType = CATEGORY_FILTER_TO_EVENT[activeKpiFilter]
    const relevantEvents = eventsState.events.filter(event => event.event_type === eventType)

    if (activeKpiFilter === "EXITS") {
      return relevantEvents
        .filter(event => matchesCategoryEventSearch(search, event))
        .map(event => {
          const product = eventToProduct(event)
          return { kind: "product" as const, key: `${product.asin}-exit-${event.snapshot_date}`, product }
        })
    }

    if (activeKpiFilter === "EXIT_TOP10") {
      const productsByAsin = new Map(snapshot.products.map(p => [p.asin, p]))
      return relevantEvents
        .filter(event => matchesCategoryEventSearch(search, event))
        .map(event => {
          const product = productsByAsin.get(event.asin)
          if (product) return { kind: "product" as const, key: `${product.asin}-${product.rank_position}`, product }
          const fallbackProduct = eventToProduct(event)
          return { kind: "product" as const, key: `${fallbackProduct.asin}-exit10-${event.snapshot_date}`, product: fallbackProduct }
        })
    }

    const eventAsins = new Set(relevantEvents.map(event => event.asin))
    return filteredProducts
      .filter(product => eventAsins.has(product.asin))
      .map(product => ({ kind: "product", key: `${product.asin}-${product.rank_position}`, product }))
  }, [snapshot, activeKpiFilter, filteredProducts, eventsState.events, search])

  const totalFilteredCount = useMemo(() => {
    if (!snapshot) return 0
    if (activeKpiFilter === "ALL") return snapshot.products.length
    const eventType = CATEGORY_FILTER_TO_EVENT[activeKpiFilter]
    if (activeKpiFilter === "EXITS" || activeKpiFilter === "EXIT_TOP10") {
      return eventsState.events.filter(event => event.event_type === eventType).length
    }
    const eventAsins = new Set(
      eventsState.events.filter(event => event.event_type === eventType).map(event => event.asin)
    )
    return snapshot.products.filter(product => eventAsins.has(product.asin)).length
  }, [snapshot, activeKpiFilter, eventsState.events])


  if (trackers.length === 0) return (
    <>
      {showCreate && (
        <CreateCategoryTrackerModal
          onClose={() => setShowCreate(false)}
          onCreate={t => {
            setTrackers(prev => [t, ...prev])
            setSelectedCode(t.tracker_code)
            setJustAdded(t.tracker_code)
            setTimeout(() => setJustAdded(null), 5000)
            setShowCreate(false)
          }}
        />
      )}
      <div className="anim-fade">
        <PageHeader title="Category Tracker" sub="Daily BSR movement across selected Amazon categories"
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
                <TrendingUp size={40} style={{ margin: "0 auto 16px", opacity: 0.3 }} />
                <div style={{ fontSize: 15, fontWeight: 600, color: T.text1, marginBottom: 6 }}>No category trackers yet</div>
                <div style={{ fontSize: 12, color: error ? T.red : T.text3, marginBottom: 24 }}>
                  {error ?? "Create a tracker to start monitoring BSR rankings."}
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
        <CreateCategoryTrackerModal
          onClose={() => setShowCreate(false)}
          onCreate={t => {
            setTrackers(prev => [t, ...prev])
            setSelectedCode(t.tracker_code)
            setJustAdded(t.tracker_code)
            setTimeout(() => setJustAdded(null), 5000)
            setShowCreate(false)
          }}
        />
      )}
      {showEdit && selectedTracker && (
        <EditCategoryTrackerModal
          tracker={selectedTracker}
          onClose={() => setShowEdit(false)}
          onUpdate={t => { setTrackers(prev => prev.map(x => x.tracker_code === t.tracker_code ? t : x)); setShowEdit(false) }}
          onDelete={code => { setTrackers(prev => prev.filter(x => x.tracker_code !== code)); setSelectedCode(""); setShowEdit(false) }}
        />
      )}
    <div className="anim-fade">
      <PageHeader title="Category Tracker" sub="Daily BSR movement across selected Amazon categories"
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

      {/* Tracker selector */}
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

      {/* Tracker info card */}
      {selectedTracker && (
        <div className="card-soft" style={{ marginBottom: 16, padding: "14px 18px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 2 }}>
                <span style={{ fontSize: 15, fontWeight: 700, color: T.text0 }}>{selectedTracker.name}</span>
                <Badge type="top10" text={selectedTracker.marketplace.toUpperCase()} />
                {selectedTracker.status === "ACTIVE" && <span className="dot-live" />}
              </div>
              <div style={{ fontSize: 12, color: T.text2, marginTop: 4 }}>
                Amazon {marketplaceLabel(selectedTracker.marketplace)}
                {" · Top "}
                {selectedTracker.tracking_config.top_n}
                {" · "}
                {selectedTracker.schedule.frequency.charAt(0) + selectedTracker.schedule.frequency.slice(1).toLowerCase()}
                {" at "}
                {String(selectedTracker.schedule.hour_utc).padStart(2, "0")}:00 UTC
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              {selectedTracker.stats.last_success_at && (
                <div style={{ fontSize: 11, color: T.text2 }}>
                  Last captured: <span style={{ color: T.text1 }}>{new Date(selectedTracker.stats.last_success_at).toLocaleDateString()}</span>
                </div>
              )}
              <div style={{ fontSize: 11, color: T.text3, marginTop: 2 }}>
                Source: Apify · {selectedTracker.stats.snapshot_count} snapshot{selectedTracker.stats.snapshot_count !== 1 ? "s" : ""}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Snapshot summary KPIs */}
      {snapshot && (
        <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
          {[
            { key: "ALL" as const, label: "Total ASINs", v: snapshot.summary.asin_count, color: T.text0, icon: <TrendingUp size={14} /> },
            { key: "NEW_ENTRANTS" as const, label: "New Entrants", v: snapshot.summary.new_entrant_count, color: T.green, icon: <Zap size={14} /> },
            { key: "RETURNING" as const, label: "Returning", v: snapshot.summary.returning_count, color: "#90EE90", icon: <RefreshCw size={14} /> },
            { key: "EXITS" as const, label: "Exits", v: snapshot.summary.exit_count, color: T.red, icon: <TrendingDown size={14} /> },
            { key: "ENTER_TOP10" as const, label: "Enter Top 10", v: snapshot.summary.enter_top10_count, color: T.amber, icon: <Star size={14} /> },
            { key: "EXIT_TOP10" as const, label: "Exit Top 10", v: snapshot.summary.exit_top10_count, color: T.red, icon: <TrendingDown size={14} /> },
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
        <div style={{ display: "flex", gap: 12, marginBottom: 8, fontSize: 11, color: T.text3, fontFamily: T.mono, flexWrap: "wrap", alignItems: "center" }}>
          <span>Snapshot: {snapshot.snapshot_date}</span>
          <span>·</span>
          <span>Captured: {new Date(snapshot.captured_at).toLocaleString()}</span>
          <span>·</span>
          <span>Compare: {rankTimeframe.toLowerCase()}</span>
          {(snapshot.source_refs?.provider || snapshot.source_refs?.apify_run_id) && (
            <span style={{ position: "relative", display: "inline-flex" }}>
              <button type="button" onClick={() => setShowMetaDetail(v => !v)}
                style={{ background: "none", border: "none", cursor: "pointer", color: T.text3, display: "inline-flex", alignItems: "center", gap: 3, padding: "2px 4px", borderRadius: 4, transition: "color .15s" }}
                onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.color = T.text1 }}
                onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.color = T.text3 }}>
                <Info size={11} /> Details
              </button>
              {showMetaDetail && (
                <div style={{ position: "absolute", top: "100%", left: 0, marginTop: 6, padding: "8px 10px", background: T.bg3, border: `1px solid ${T.border}`, borderRadius: 6, fontSize: 10, color: T.text2, fontFamily: T.mono, whiteSpace: "nowrap", zIndex: 20, boxShadow: "0 4px 12px rgba(0,0,0,.4)" }}>
                  {snapshot.source_refs?.provider && <div>Provider: {snapshot.source_refs.provider}</div>}
                  {snapshot.source_refs?.apify_run_id && <div>Run: {snapshot.source_refs.apify_run_id}</div>}
                </div>
              )}
            </span>
          )}
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
          <div style={{ display: "flex", gap: 4 }}>
            {(["WEEKLY", "MONTHLY"] as Timeframe[]).map(t => (
              <button key={t} onClick={() => { if (t !== rankTimeframe) { setSnapshot(null); setLoading(true); setRankTimeframe(t) } }}
                style={{ padding: "5px 10px", borderRadius: 6, border: `1px solid ${t === rankTimeframe ? T.amber : T.border}`, background: t === rankTimeframe ? T.bg4 : "transparent", color: t === rankTimeframe ? T.amber : T.text3, fontSize: 11, fontWeight: 600, cursor: "pointer", textTransform: "capitalize" }}>
                {t === "WEEKLY" ? "7 days" : "30 days"}
              </button>
            ))}
          </div>
          <span style={{ fontSize: 11, color: T.text3, fontFamily: T.mono, marginLeft: "auto" }}>
            {allVisibleRows.length} of {totalFilteredCount} {activeKpiFilter === "ALL" ? "products" : "matched rows"}
          </span>
        </div>

        {justAdded && (
          <div style={{ background: `${T.blue}15`, border: `1px solid ${T.blue}40`, borderRadius: 8, padding: "12px 14px", marginBottom: 16, color: T.blue, fontSize: 12 }}>
            Data will be collected and displayed in a few minutes.
          </div>
        )}

        {loading ? (
          <div style={{ textAlign: "center", padding: 40, color: T.text3 }}>Loading snapshot...</div>
        ) : (
          <div style={{ width: "100%", overflowX: "auto" }}>
            <table style={{ width: "100%", minWidth: 1260, borderCollapse: "collapse" }}>
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
                    const rankLabel = event.payload.current_rank ?? event.payload.previous_rank ?? event.payload.rank_today ?? null
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
                    <a href={p.product_url} target="_blank" rel="noopener noreferrer" style={{ color: T.blue, textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 3 }}>
                      {p.asin}<ExternalLink size={9} />
                    </a>
                  </td>
                  <td style={{ padding: "9px 10px", fontSize: 12, color: T.text0, maxWidth: 240 }}>
                    <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.title}</div>
                  </td>
                  <td style={{ padding: "9px 10px", fontSize: 11, color: T.text2, width: 90, maxWidth: 90 }}>
                    <a href={p.brand} target="_blank" rel="noopener noreferrer"
                      style={{ color: T.blue, textDecoration: "none", display: "inline-block", width: "100%", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {extractBrandName(p.brand)}
                    </a>
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
                        <div style={{ minWidth: 180 }}>
                          <button
                            type="button"
                            onClick={() => setOpenDealKey(prev => prev === dealKey ? null : dealKey)}
                            style={{
                              padding: "4px 8px",
                              borderRadius: 6,
                              border: `1px solid ${T.blue}`,
                              background: `${T.blue}16`,
                              color: T.blue,
                              fontSize: 10,
                              fontFamily: T.mono,
                              fontWeight: 600,
                              cursor: "pointer",
                            }}
                          >
                            {isOpen ? "Hide" : "View"} Deal
                          </button>
                          {isOpen && (
                            <div
                              style={{
                                marginTop: 6,
                                padding: "6px 8px",
                                background: T.bg3,
                                border: `1px solid ${T.border}`,
                                borderRadius: 6,
                                color: T.text1,
                                lineHeight: 1.4,
                              }}
                            >
                              {dealItems.map((deal, idx) => (
                                <div key={`${deal}-${idx}`} style={{ marginBottom: idx < dealItems.length - 1 ? 4 : 0 }}>
                                  • {deal}
                                </div>
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
                        <div style={{ minWidth: 180 }}>
                          <button
                            type="button"
                            onClick={() => setOpenCouponKey(prev => prev === couponKey ? null : couponKey)}
                            style={{
                              padding: "4px 8px",
                              borderRadius: 6,
                              border: `1px solid ${T.amberD}`,
                              background: `${T.amber}14`,
                              color: T.amber,
                              fontSize: 10,
                              fontFamily: T.mono,
                              fontWeight: 600,
                              cursor: "pointer",
                            }}
                          >
                            {isOpen ? "Hide" : "View"} {couponItems.length} Coupon{couponItems.length > 1 ? "s" : ""}
                          </button>
                          {isOpen && (
                            <div
                              style={{
                                marginTop: 6,
                                padding: "6px 8px",
                                background: T.bg3,
                                border: `1px solid ${T.border}`,
                                borderRadius: 6,
                                color: T.text1,
                                lineHeight: 1.4,
                              }}
                            >
                              {couponItems.map((coupon, idx) => (
                                <div key={`${coupon}-${idx}`} style={{ marginBottom: idx < couponItems.length - 1 ? 4 : 0 }}>
                                  • {coupon}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )
                    })()}
                  </td>
                  </tr>
                )})}
              </tbody>
            </table>
          </div>
        )}

        {!loading && !snapshot && (
          <div style={{ textAlign: "center", padding: "48px 0", color: T.text3, fontSize: 13 }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>📭</div>
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

export const CategoryPage = () => (
  <Suspense fallback={<div style={{ textAlign: "center", padding: 40, color: T.text3 }}>Loading...</div>}>
    <CategoryPageInner />
  </Suspense>
)
