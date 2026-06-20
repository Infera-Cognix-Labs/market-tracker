"use client"

import { Info, Plus, Search, X } from "lucide-react"
import { Suspense, useState } from "react"
import { ProductTable } from "../categories/ProductTable"
import { ConfirmDialog } from "../shared/ConfirmDialog"
import { T } from "../shared/DesignTokens"
import { Dropdown } from "../shared/Dropdown"
import { ErrorBanner } from "../shared/ErrorBanner"
import { SnapshotMetadataBar } from "../shared/SnapshotMetadataBar"
import { TrackerInfoCard, TrackerStat } from "../shared/TrackerInfoCard"
import { TrackerPageLayout } from "../shared/TrackerPageLayout"
import {
  apiCreateKeywordTracker,
  apiDeleteKeywordTracker,
  apiGetLatestKeywordSnapshot,
  apiListEvents,
  apiListKeywordTrackers,
  apiTriggerJob,
  apiUpdateKeywordTracker,
} from "../shared/api"
import { HOURS, inputStyle, labelStyle, MARKETPLACES } from "../shared/formatting"
import { handleApiError, useTrackerPage } from "../shared/hooks"
import type {
  KeywordTracker,
  KeywordTrackerCreateRequest,
  KeywordTrackerUpdateRequest,
  TrackerStatus
} from "../shared/types"

type KpiFilter = "ALL" | "NEW_ENTRANTS" | "RETURNING" | "EXITS" | "ENTER_TOP10" | "EXIT_TOP10"

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
      handleApiError(err, setError, "A tracker for this keyword already exists.")
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
            {error && <ErrorBanner message={error} />}
            <div style={{ display: "flex", gap: 10, justifyContent: "space-between" }}>
              <button type="button" onClick={() => setShowConfirm(true)}
                style={{ padding: "9px 14px", borderRadius: 8, border: `1px solid ${T.red}40`, background: "transparent", color: T.red, fontSize: 12, cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 4, fontFamily: T.sans }}>
                Delete
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

export const KeywordPageInner = () => {
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
  } = useTrackerPage<KeywordTracker>({
    trackerType: "KEYWORD",
    apiListTrackers: apiListKeywordTrackers,
    apiGetSnapshot: apiGetLatestKeywordSnapshot,
    apiListEvents,
    apiTriggerJob,
    listErrorMsg: "Failed to load keyword trackers",
  })

  if (trackers.length === 0) return (
    <>
      {showCreate && (
        <CreateKeywordTrackerModal onClose={() => setShowCreate(false)} onCreate={t => { handleCreate(t); setLoading(true) }} />
      )}
      <div className="anim-fade">
        <div className="card" style={{ textAlign: "center", padding: "80px 24px", color: T.text3 }}>
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
        <CreateKeywordTrackerModal onClose={() => setShowCreate(false)} onCreate={t => { handleCreate(t); setLoading(true) }} />
      )}
      {showEdit && selectedTracker && (
        <EditKeywordTrackerModal
          tracker={selectedTracker as KeywordTracker}
          onClose={() => setShowEdit(false)}
          onUpdate={handleUpdate as (t: KeywordTracker) => void}
          onDelete={handleDelete}
        />
      )}
      <TrackerPageLayout
        title="Keyword Tracker"
        sub="Monitor Amazon search results for keywords"
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
        onKpiFilterChange={f => setActiveKpiFilter(f as KpiFilter)}
        eventsState={eventsState}
        onEventsRetry={() => setActiveKpiFilter(prev => prev)}
      >
        {error && <ErrorBanner message={error} />}

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
        justAdded={justAdded}
        hasSnapshot={!!snapshot}
        triggering={triggering}
        onTrigger={handleTriggerJob}
        productUrlResolver={(p) => p.product_url || `https://www.amazon.com/dp/${p.asin}`}
      />
    </>
  )
}

export const KeywordPage = () => (
  <Suspense fallback={<div style={{ textAlign: "center", padding: 40, color: T.text3 }}>Loading...</div>}>
    <KeywordPageInner />
  </Suspense>
)
