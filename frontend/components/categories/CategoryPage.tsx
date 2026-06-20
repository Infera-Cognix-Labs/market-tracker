"use client"

import { AlertCircle, CheckCircle, ExternalLink, Info, Plus, Search, TrendingUp, X } from "lucide-react"
import { Suspense, useState } from "react"
import { ConfirmDialog } from "../shared/ConfirmDialog"
import { DeleteButton } from "../shared/DeleteButton"
import { T, marketplaceLabel } from "../shared/DesignTokens"
import { Dropdown } from "../shared/Dropdown"
import { ErrorBanner } from "../shared/ErrorBanner"
import { SnapshotMetadataBar } from "../shared/SnapshotMetadataBar"
import { StatusToggle } from "../shared/StatusToggle"
import { TrackerInfoCard, TrackerStat } from "../shared/TrackerInfoCard"
import { TrackerPageLayout } from "../shared/TrackerPageLayout"
import { apiCreateCategoryTracker, apiDeleteCategoryTracker, apiGetLatestCategorySnapshot, apiListCategoryTrackers, apiListEvents, apiTriggerJob, apiUpdateCategoryTracker } from "../shared/api"
import { HOURS, MARKETPLACES, inputStyle, labelStyle, parseBestsellerUrl } from "../shared/formatting"
import { handleApiError, useTrackerPage } from "../shared/hooks"
import type { CategoryTracker, CategoryTrackerCreateRequest, CategoryTrackerUpdateRequest, Timeframe, TrackerStatus } from "../shared/types"
import { ProductTable } from "./ProductTable"

type CategoryKpiFilter = "ALL" | "NEW_ENTRANTS" | "RETURNING" | "EXITS" | "ENTER_TOP10" | "EXIT_TOP10"

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
      handleApiError(err, setError, "A tracker for this marketplace and URL already exists.")
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

export const CategoryPageInner = () => {
  const [rankTimeframe, setRankTimeframe] = useState<Timeframe>("WEEKLY")

  const {
    trackers, selectedCode,
    loading, error,
    snapshot, snapshotLoading,
    search, setSearch,
    showCreate, setShowCreate, showEdit, setShowEdit,
    statusFilter, setStatusFilter,
    activeKpiFilter, setActiveKpiFilter,
    eventsState,
    justAdded,
    openCouponKey, setOpenCouponKey,
    openDealKey, setOpenDealKey,
    triggering, handleTriggerJob,
    showMetaDetail, setShowMetaDetail,
    selectedTracker,
    allVisibleRows, totalFilteredCount,
    handleSelectTracker, handleCreate, handleUpdate, handleDelete,
    setLoading,
  } = useTrackerPage<CategoryTracker>({
    trackerType: "CATEGORY",
    apiListTrackers: apiListCategoryTrackers,
    apiGetSnapshot: (code) => apiGetLatestCategorySnapshot(code, rankTimeframe),
    apiListEvents,
    apiTriggerJob,
    listErrorMsg: "Failed to load category trackers",
  })

  if (trackers.length === 0) return (
    <>
      {showCreate && (
        <CreateCategoryTrackerModal
          onClose={() => setShowCreate(false)}
          onCreate={t => { handleCreate(t); setLoading(true) }}
        />
      )}
      <div className="anim-fade">
        <div className="card" style={{ textAlign: "center", padding: "80px 24px", color: T.text3 }}>
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
          onCreate={t => { handleCreate(t); setLoading(true) }}
        />
      )}
      {showEdit && selectedTracker && (
        <EditCategoryTrackerModal
          tracker={selectedTracker as CategoryTracker}
          onClose={() => setShowEdit(false)}
          onUpdate={t => { handleUpdate(t as CategoryTracker); setLoading(true) }}
          onDelete={code => { handleDelete(code); setLoading(true) }}
        />
      )}
      <TrackerPageLayout
        title="Category Tracker"
        sub="Daily BSR movement across selected Amazon categories"
        trackers={trackers}
        selectedCode={selectedCode}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        onSelectTracker={handleSelectTracker}
        onEdit={() => setShowEdit(true)}
        onCreate={() => setShowCreate(true)}
        selectedTracker={selectedTracker}
        snapshot={snapshot}
        activeKpiFilter={activeKpiFilter}
        onKpiFilterChange={f => setActiveKpiFilter(f as CategoryKpiFilter)}
        eventsState={eventsState}
        onEventsRetry={() => setActiveKpiFilter(prev => prev)}
      >
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
      </TrackerPageLayout>

      <ProductTable
        search={search}
        onSearchChange={setSearch}
        allVisibleRows={allVisibleRows}
        totalFilteredCount={totalFilteredCount}
        activeKpiFilter={activeKpiFilter}
        loading={snapshotLoading}
        openCouponKey={openCouponKey}
        openDealKey={openDealKey}
        onOpenCouponKeyChange={setOpenCouponKey}
        onOpenDealKeyChange={setOpenDealKey}
        minWidth={1260}
        headerExtra={
          <div style={{ display: "flex", gap: 4 }}>
            {(["WEEKLY", "MONTHLY"] as Timeframe[]).map(t => (
              <button key={t} onClick={() => { if (t !== rankTimeframe) { setRankTimeframe(t) } }}
                style={{ padding: "5px 10px", borderRadius: 6, border: `1px solid ${t === rankTimeframe ? T.amber : T.border}`, background: t === rankTimeframe ? T.bg4 : "transparent", color: t === rankTimeframe ? T.amber : T.text3, fontSize: 11, fontWeight: 600, cursor: "pointer", textTransform: "capitalize" }}>
                {t === "WEEKLY" ? "7 days" : "30 days"}
              </button>
            ))}
          </div>
        }
        justAdded={justAdded}
        hasSnapshot={!!snapshot}
        triggering={triggering}
        onTrigger={handleTriggerJob}
      />
    </>
  )
}

export const CategoryPage = () => (
  <Suspense fallback={<div style={{ textAlign: "center", padding: 40, color: T.text3 }}>Loading...</div>}>
    <CategoryPageInner />
  </Suspense>
)
