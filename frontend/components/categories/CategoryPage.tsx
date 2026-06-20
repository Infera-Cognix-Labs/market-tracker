"use client"

import { AlertCircle, CheckCircle, Edit2, ExternalLink, Info, Plus, Search, TrendingDown, TrendingUp, X } from "lucide-react"
import { Suspense, useEffect, useMemo, useReducer, useState } from "react"
import { Badge } from "../shared/Badge"
import { ConfirmDialog } from "../shared/ConfirmDialog"
import { DeleteButton } from "../shared/DeleteButton"
import { T, marketplaceLabel } from "../shared/DesignTokens"
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
import { StatusToggle } from "../shared/StatusToggle"
import { TrackerInfoCard, TrackerStat } from "../shared/TrackerInfoCard"
import { TrackerSelector } from "../shared/TrackerSelector"
import { ApiError, apiCreateCategoryTracker, apiDeleteCategoryTracker, apiGetLatestCategorySnapshot, apiListCategoryTrackers, apiListEvents, apiTriggerJob, apiUpdateCategoryTracker } from "../shared/api"
import { FILTER_TO_EVENT, HOURS, MARKETPLACES, eventToProduct, extractBrandName, getEventImageUrl, inputStyle, labelStyle, matchesEventSearch, matchesProductSearch, parseBestsellerUrl, parseCouponItems, parseDealItems, rankTrendMeta } from "../shared/formatting"
import type { CategorySnapshot, CategorySnapshotProduct, CategoryTracker, CategoryTrackerCreateRequest, CategoryTrackerUpdateRequest, Event, EventType, Timeframe, TrackerStatus } from "../shared/types"

type CategoryKpiFilter = "ALL" | "NEW_ENTRANTS" | "RETURNING" | "EXITS" | "ENTER_TOP10" | "EXIT_TOP10"

type CategoryTableRow =
  | { kind: "product"; key: string; product: CategorySnapshotProduct }
  | { kind: "event"; key: string; event: Event }

const CATEGORY_FILTER_TO_EVENT = FILTER_TO_EVENT as Record<Exclude<CategoryKpiFilter, "ALL">, EventType>

interface CreateModalProps { onClose: () => void; onCreate: (t: CategoryTracker) => void }

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
            {error && <ErrorBanner message={error} />}
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
              <StatusToggle value={status} onChange={setStatus} />
            </div>
            {error && <ErrorBanner message={error} />}
            <div style={{ display: "flex", gap: 10, justifyContent: "space-between" }}>
              <DeleteButton onClick={() => setShowConfirm(true)} />
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

  const selectedTracker = trackers.find(t => t.tracker_code === selectedCode)

  const filteredProducts = useMemo(() => {
    if (!snapshot) return []
    return snapshot.products.filter(product => matchesProductSearch(search, product))
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
        .filter(event => matchesEventSearch(search, event))
        .map(event => {
          const product = eventToProduct(event)
          return { kind: "product" as const, key: `${product.asin}-exit-${event.snapshot_date}`, product }
        })
    }

    if (activeKpiFilter === "EXIT_TOP10") {
      const productsByAsin = new Map(snapshot.products.map(p => [p.asin, p]))
      return relevantEvents
        .filter(event => matchesEventSearch(search, event))
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

        {/* Status filter tabs */}
        <StatusFilterTabs trackers={trackers} value={statusFilter} onChange={setStatusFilter} />

        {/* Tracker selector */}
        <TrackerSelector trackers={trackers} statusFilter={statusFilter} selectedCode={selectedCode} onSelect={code => { setSnapshot(null); setLoading(true); setSelectedCode(code); setRefreshKey(k => k + 1) }} />

        {/* Tracker info card */}
        {selectedTracker && (
          <TrackerInfoCard
            name={selectedTracker.name}
            marketplace={selectedTracker.marketplace}
            status={selectedTracker.status}
            meta={`Amazon ${marketplaceLabel(selectedTracker.marketplace)} · Top ${selectedTracker.tracking_config.top_n} · ${selectedTracker.schedule.frequency.charAt(0) + selectedTracker.schedule.frequency.slice(1).toLowerCase()} at ${String(selectedTracker.schedule.hour_utc).padStart(2, "0")}:00 UTC`}
            statsRight={
              <>
                {selectedTracker.stats.last_success_at && (
                  <TrackerStat label="Last capture" value={new Date(selectedTracker.stats.last_success_at).toLocaleDateString()} />
                )}
                <TrackerStat label="Snapshots" value={selectedTracker.stats.snapshot_count} />
              </>
            }
          >
            {selectedTracker.scope.browse_node_url && (
              <a href={selectedTracker.scope.browse_node_url} target="_blank" rel="noopener noreferrer"
                style={{ fontSize: 11, color: T.text3, textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 3, marginTop: 2, transition: "color .15s" }}
                onMouseEnter={e => { (e.currentTarget as HTMLAnchorElement).style.color = T.blue }}
                onMouseLeave={e => { (e.currentTarget as HTMLAnchorElement).style.color = T.text3 }}>
                <ExternalLink size={10} /> Category URL
              </a>
            )}
          </TrackerInfoCard>
        )}

        {/* Snapshot summary KPIs */}
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
            onFilterChange={f => setActiveKpiFilter(f as CategoryKpiFilter)}
          />
        )}

        {/* Snapshot metadata */}
        {snapshot && (
          <SnapshotMetadataBar
            snapshotDate={snapshot.snapshot_date}
            capturedAt={snapshot.captured_at}
            sourceRefs={
              <>
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
              </>
            }
          />
        )}

        {/* Events loading/error banner */}
        <EventsStatusBanner loading={eventsState.loading} error={eventsState.error} onRetry={() => setActiveKpiFilter(prev => prev)} />

        {/* Products table */}
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}`, display: "flex", alignItems: "center", gap: 10 }}>
            <SearchInput value={search} onChange={setSearch} placeholder="Search ASIN, title, or brand..." />
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

        {justAdded && <InfoBanner message="Data will be collected and displayed in a few minutes." />}

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
    </>
  )
}

export const CategoryPage = () => (
  <Suspense fallback={<div style={{ textAlign: "center", padding: 40, color: T.text3 }}>Loading...</div>}>
    <CategoryPageInner />
  </Suspense>
)
