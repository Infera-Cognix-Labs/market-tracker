"use client"

import { AlertCircle, Edit2, ExternalLink, Info, Plus, Search, Trash2, TrendingDown, TrendingUp, X } from "lucide-react"
import { Suspense, useEffect, useMemo, useReducer, useState } from "react"
import { Badge } from "../shared/Badge"
import { ConfirmDialog } from "../shared/ConfirmDialog"
import { T } from "../shared/DesignTokens"
import { Dropdown } from "../shared/Dropdown"
import { ErrorBanner } from "../shared/ErrorBanner"
import { EventsStatusBanner } from "../shared/EventsStatusBanner"
import { InfoBanner } from "../shared/InfoBanner"
import { KpiFilterBar } from "../shared/KpiFilterBar"
import { NoSnapshotPlaceholder } from "../shared/NoSnapshotPlaceholder"
import { PageHeader } from "../shared/PageHeader"
import { SearchInput } from "../shared/SearchInput"
import { SnapshotMetadataBar } from "../shared/SnapshotMetadataBar"
import { StatusFilterTabs } from "../shared/StatusFilterTabs"
import { TrackerInfoCard, TrackerStat } from "../shared/TrackerInfoCard"
import { TrackerSelector } from "../shared/TrackerSelector"
import {
  apiCreateKeywordTracker,
  apiDeleteKeywordTracker,
  ApiError,
  apiGetLatestKeywordSnapshot,
  apiListEvents,
  apiListKeywordTrackers,
  apiTriggerJob,
  apiUpdateKeywordTracker,
} from "../shared/api"
import { eventToProduct, extractBrandName, FILTER_TO_EVENT, getEventImageUrl, HOURS, inputStyle, labelStyle, MARKETPLACES, matchesEventSearch, matchesProductSearch, parseCouponItems, parseDealItems, rankTrendMeta } from "../shared/formatting"
import type {
  CategorySnapshot,
  CategorySnapshotProduct,
  Event,
  EventType,
  KeywordTracker,
  KeywordTrackerCreateRequest,
  KeywordTrackerUpdateRequest,
  TrackerStatus
} from "../shared/types"

type KpiFilter = "ALL" | "NEW_ENTRANTS" | "RETURNING" | "EXITS" | "ENTER_TOP10" | "EXIT_TOP10"

type TableRow =
  | { kind: "product"; key: string; product: CategorySnapshotProduct }
  | { kind: "event"; key: string; event: Event }

const KEYWORD_FILTER_TO_EVENT = FILTER_TO_EVENT as Record<Exclude<KpiFilter, "ALL">, EventType>

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
              <Dropdown label="Marketplace" value={marketplace} onChange={v => setMarketplace(v as string)} options={MARKETPLACES} />
            </div>
            <div style={{ marginBottom: 20 }}>
              <Dropdown label="Run at (UTC hour)" value={hourUtc} onChange={v => setHourUtc(Number(v))} options={HOURS} />
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
interface EditModalProps { tracker: KeywordTracker; onClose: () => void; onUpdate: (t: KeywordTracker) => void; onDelete: (trackerCode: string) => void }

const EditKeywordTrackerModal = ({ tracker, onClose, onUpdate, onDelete }: EditModalProps) => {
  const [name, setName] = useState(tracker.name)
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

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await apiDeleteKeywordTracker(tracker.tracker_code)
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
            <div style={{ marginBottom: 20 }}>
              <Dropdown label="Run at (UTC hour)" value={hourUtc} onChange={v => setHourUtc(Number(v))} options={HOURS} />
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
        message={<>Delete &quot;<b>{tracker.name}</b>&quot; and all its snapshots? This action cannot be undone.</>}
        confirmLabel="Delete"
        loading={deleting}
        onConfirm={handleDelete}
        onCancel={() => setShowConfirm(false)}
      />
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
  const [showMetaDetail, setShowMetaDetail] = useState(false)

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
          events: res.items.filter(event => Object.values(KEYWORD_FILTER_TO_EVENT).includes(event.event_type)),
        })
      })
      .catch(() => {
        if (cancelled) return
        dispatchEvents({ type: "FETCH_ERR", error: "Failed to load events" })
      })
    return () => { cancelled = true }
  }, [selectedCode, snapshot?.snapshot_date, activeKpiFilter])

  const selectedTracker = trackers.find(t => t.tracker_code === selectedCode)

  const products = useMemo(() => snapshot?.products ?? [], [snapshot])

  const filteredProducts = useMemo(() => {
    return products.filter(p => matchesProductSearch(search, p))
  }, [products, search])

  const allVisibleRows = useMemo<TableRow[]>(() => {
    if (!snapshot) return []
    if (activeKpiFilter === "ALL") {
      return filteredProducts.map(p => ({ kind: "product", key: p.asin, product: p }))
    }

    const eventType = KEYWORD_FILTER_TO_EVENT[activeKpiFilter]
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
    const eventType = KEYWORD_FILTER_TO_EVENT[activeKpiFilter]
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
          onDelete={code => {
            setTrackers(prev => prev.filter(t => t.tracker_code !== code))
            setSelectedCode("")
            setSnapshot(null)
            setShowEdit(false)
          }}
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
        <StatusFilterTabs trackers={trackers} value={statusFilter} onChange={setStatusFilter} />

        {/* Tracker selector */}
        <TrackerSelector trackers={trackers} statusFilter={statusFilter} selectedCode={selectedCode} onSelect={code => { setSnapshot(null); setLoading(true); setSelectedCode(code); setRefreshKey(k => k + 1) }} />

        {/* Error */}
        {error && <ErrorBanner message={error} />}

        {/* Tracker info card */}
        {selectedTracker && (
          <TrackerInfoCard
            name={selectedTracker.name}
            status={selectedTracker.status}
            meta={`"${selectedTracker.scope.keyword}" · Top ${selectedTracker.tracking_config.top_n} · ${selectedTracker.schedule.frequency.charAt(0) + selectedTracker.schedule.frequency.slice(1).toLowerCase()} at ${String(selectedTracker.schedule.hour_utc).padStart(2, "0")}:00 UTC`}
            statsRight={
              <>
                {selectedTracker.stats.last_success_at && (
                  <TrackerStat label="Last capture" value={new Date(selectedTracker.stats.last_success_at).toLocaleDateString()} />
                )}
                <TrackerStat label="Snapshots" value={selectedTracker.stats.snapshot_count} />
              </>
            }
          />
        )}

        {/* Snapshot summary KPIs */}
        {snapshot && (
          <KpiFilterBar
            summary={{
              asin_count: snapshot.summary.asin_count,
              new_entrants: newEntrantCount,
              returning: returningCount,
              exits: exitCount,
              enter_top10: enterTop10Count,
              exit_top10: exitTop10Count,
            }}
            activeFilter={activeKpiFilter}
            onFilterChange={f => setActiveKpiFilter(f as KpiFilter)}
          />
        )}

        {/* Snapshot metadata */}
        {snapshot && (
          <SnapshotMetadataBar
            snapshotDate={snapshot.snapshot_date}
            capturedAt={snapshot.captured_at}
            sourceRefs={
              (snapshot.source_refs?.provider || snapshot.source_refs?.apify_run_id) ? (
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
              ) : undefined
            }
          />
        )}

        {/* Events loading/error banner */}
        <EventsStatusBanner loading={eventsState.loading} error={eventsState.error} onRetry={() => setActiveKpiFilter(prev => prev)} />

        {/* Products table */}
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}`, display: "flex", alignItems: "center", gap: 10 }}>
            <SearchInput value={search} onChange={setSearch} placeholder="Search ASIN, title, or brand..." />
            <span style={{ fontSize: 11, color: T.text3, fontFamily: T.mono, marginLeft: "auto" }}>
              {allVisibleRows.length} of {totalFilteredCount} {activeKpiFilter === "ALL" ? "products" : "matched rows"}
            </span>
          </div>

          {justAdded && <InfoBanner message="Data will be collected and displayed in a few minutes." />}

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

          {!loading && !snapshot && <NoSnapshotPlaceholder triggering={triggering} onTrigger={handleTriggerJob} />}
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
