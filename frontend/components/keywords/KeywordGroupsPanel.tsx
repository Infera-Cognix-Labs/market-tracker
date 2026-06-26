"use client"

import { AlertCircle, Edit2, Layers3, Plus, Settings, Trash2, X } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { ProductTable } from "../categories/ProductTable"
import { ConfirmDialog } from "../shared/ConfirmDialog"
import { T } from "../shared/DesignTokens"
import { Dropdown } from "../shared/Dropdown"
import { ErrorBanner } from "../shared/ErrorBanner"
import { KpiFilterBar } from "../shared/KpiFilterBar"
import { PageHeader } from "../shared/PageHeader"
import { SnapshotMetadataBar } from "../shared/SnapshotMetadataBar"
import { StatusFilterTabs } from "../shared/StatusFilterTabs"
import { TrackerInfoCard, TrackerStat } from "../shared/TrackerInfoCard"
import {
  apiCreateKeywordGroup,
  apiDeleteKeywordGroup,
  apiGetLatestKeywordGroupSnapshot,
  apiGetLatestKeywordSnapshot,
  apiListKeywordGroups,
  apiListKeywordTrackers,
  apiReplaceTrackedKeywords,
  apiUpdateKeywordGroup,
} from "../shared/api"
import { MARKETPLACES } from "../shared/formatting"
import { handleApiError } from "../shared/hooks"
import type { CategorySnapshot, KeywordGroup, KeywordGroupCreateRequest, KeywordGroupSnapshot, KeywordGroupUpdateRequest, KeywordTracker, Timeframe, TrackerStatus, TrackedKeyword, TrackedKeywordInput } from "../shared/types"

type GroupSelectorItem = { tracker_code: string; name: string; status?: string }

const groupToSelector = (group: KeywordGroup): GroupSelectorItem => ({ tracker_code: group.group_code, name: group.name, status: group.status })
const keywordLabel = (tracker: KeywordTracker) => `${tracker.name} - "${tracker.scope.keyword}"`
const STATUS_OPTIONS: TrackerStatus[] = ["ACTIVE", "PAUSED", "ARCHIVED"]
const statusColor = (status: TrackerStatus) => status === "ACTIVE" ? T.green : status === "PAUSED" ? T.amber : T.text3

const KeywordPicker = ({ trackers, selected, onToggle }: { trackers: KeywordTracker[]; selected: Set<string>; onToggle: (code: string) => void }) => (
  <div style={{ maxHeight: 260, overflowY: "auto", border: `1px solid ${T.border}`, borderRadius: 8, background: T.bg3 }}>
    {trackers.length === 0 ? (
      <div style={{ padding: 14, color: T.text3, fontSize: 12 }}>No keyword trackers in this marketplace.</div>
    ) : trackers.map(tracker => {
      const checked = selected.has(tracker.tracker_code)
      return (
        <label key={tracker.tracker_code} style={{ display: "flex", gap: 10, alignItems: "flex-start", padding: "10px 12px", borderBottom: `1px solid ${T.border}`, cursor: "pointer" }}>
          <input type="checkbox" checked={checked} onChange={() => onToggle(tracker.tracker_code)} style={{ marginTop: 2 }} />
          <span style={{ minWidth: 0 }}>
            <span style={{ display: "block", color: checked ? T.text0 : T.text1, fontSize: 12, fontWeight: checked ? 700 : 500 }}>{tracker.name}</span>
            <span style={{ display: "block", color: T.text3, fontSize: 11, marginTop: 2 }}>&quot;{tracker.scope.keyword}&quot; - {tracker.tracker_code}</span>
          </span>
        </label>
      )
    })}
  </div>
)

const CreateKeywordGroupModal = ({ keywordTrackers, onClose, onCreate }: { keywordTrackers: KeywordTracker[]; onClose: () => void; onCreate: (group: KeywordGroup) => void }) => {
  const [name, setName] = useState("")
  const [marketplace, setMarketplace] = useState(keywordTrackers[0]?.marketplace ?? "amazon_us")
  const [selectedCodes, setSelectedCodes] = useState<Set<string>>(new Set())
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const marketplaceTrackers = useMemo(() => keywordTrackers.filter(t => (t.marketplace ?? marketplace) === marketplace), [keywordTrackers, marketplace])

  const toggleCode = (code: string) => {
    setSelectedCodes(prev => {
      const next = new Set(prev)
      if (next.has(code)) next.delete(code)
      else next.add(code)
      return next
    })
    setError(null)
  }

  const handleMarketplace = (value: string | number) => {
    setMarketplace(String(value))
    setSelectedCodes(new Set())
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!name.trim()) { setError("Group name is required."); return }
    if (selectedCodes.size === 0) { setError("Select at least one keyword tracker."); return }
    const payload: KeywordGroupCreateRequest = { name: name.trim(), marketplace, tracked_keywords: Array.from(selectedCodes).map(tracker_code => ({ tracker_code, enabled: true })) }
    setSubmitting(true)
    try {
      const group = await apiCreateKeywordGroup(payload)
      onCreate(group)
    } catch (err) {
      handleApiError(err, setError, "This keyword group already exists.", "Failed to create keyword group.")
      setSubmitting(false)
    }
  }

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)", zIndex: 1000, overflowY: "auto" }}>
      <div style={{ minHeight: "100%", display: "flex", alignItems: "flex-start", justifyContent: "center", padding: "72px 24px 24px" }}>
        <div className="card" style={{ width: "100%", maxWidth: 620, padding: "24px 28px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
            <span style={{ fontSize: 16, fontWeight: 700, color: T.text0 }}>New Keyword Group</span>
            <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: T.text3, display: "flex" }}><X size={18} /></button>
          </div>
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 16 }}><label className="label">Group Name</label><input className="input" value={name} onChange={e => setName(e.target.value)} maxLength={120} placeholder="e.g. Baby bottle keywords" /></div>
            <div style={{ marginBottom: 16 }}><Dropdown label="Marketplace" value={marketplace} onChange={handleMarketplace} options={MARKETPLACES} /></div>
            <div style={{ marginBottom: 16 }}><label className="label">Keyword Trackers ({selectedCodes.size})</label><KeywordPicker trackers={marketplaceTrackers} selected={selectedCodes} onToggle={toggleCode} /></div>
            {error && <ErrorBanner message={error} />}
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button type="button" className="btn-ghost" onClick={onClose}>Cancel</button>
              <button type="submit" className="btn-primary" disabled={submitting} style={{ display: "flex", alignItems: "center", gap: 6 }}><Plus size={14} /> {submitting ? "Creating..." : "Create Group"}</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

const EditKeywordGroupModal = ({ group, onClose, onUpdate, onDelete }: { group: KeywordGroup; onClose: () => void; onUpdate: (group: KeywordGroup) => void; onDelete: (groupCode: string) => void }) => {
  const [name, setName] = useState(group.name)
  const [status, setStatus] = useState<TrackerStatus>(group.status)
  const [submitting, setSubmitting] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!name.trim()) { setError("Group name is required."); return }
    const payload: KeywordGroupUpdateRequest = { name: name.trim(), status }
    setSubmitting(true)
    try { onUpdate(await apiUpdateKeywordGroup(group.group_code, payload)) }
    catch { setError("Failed to update keyword group."); setSubmitting(false) }
  }

  const handleDelete = async () => {
    setDeleting(true)
    try { await apiDeleteKeywordGroup(group.group_code); onDelete(group.group_code) }
    catch { setError("Failed to delete keyword group."); setDeleting(false); setShowConfirm(false) }
  }

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)", zIndex: 1000, overflowY: "auto" }}>
      <div style={{ minHeight: "100%", display: "flex", alignItems: "flex-start", justifyContent: "center", padding: "72px 24px 24px" }}>
        <div className="card" style={{ width: "100%", maxWidth: 480, padding: "24px 28px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
            <div><span style={{ fontSize: 16, fontWeight: 700, color: T.text0 }}>Edit Group</span><div style={{ fontSize: 11, color: T.text3, marginTop: 2, fontFamily: T.mono }}>{group.group_code}</div></div>
            <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: T.text3, display: "flex" }}><X size={18} /></button>
          </div>
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 16 }}><label className="label">Name</label><input className="input" value={name} onChange={e => setName(e.target.value)} maxLength={120} /></div>
            <div style={{ marginBottom: 20 }}>
              <label className="label">Status</label>
              <div style={{ display: "flex", gap: 8 }}>
                {STATUS_OPTIONS.map(s => <button key={s} type="button" onClick={() => setStatus(s)} style={{ flex: 1, padding: "9px 12px", borderRadius: 8, border: `1px solid ${status === s ? statusColor(s) : T.border}`, background: status === s ? T.bg4 : T.bg3, color: status === s ? statusColor(s) : T.text2, fontSize: 12, cursor: "pointer" }}>{s}</button>)}
              </div>
            </div>
            {error && <ErrorBanner message={error} />}
            <div style={{ display: "flex", gap: 10, justifyContent: "space-between" }}>
              <button type="button" onClick={() => setShowConfirm(true)} style={{ padding: "9px 14px", borderRadius: 8, border: `1px solid ${T.red}40`, background: "transparent", color: T.red, fontSize: 12, cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 4, fontFamily: T.sans }}><Trash2 size={12} /> Delete</button>
              <div style={{ display: "flex", gap: 10 }}><button type="button" className="btn-ghost" onClick={onClose}>Cancel</button><button type="submit" className="btn-primary" disabled={submitting}>{submitting ? "Saving..." : "Save Changes"}</button></div>
            </div>
          </form>
        </div>
      </div>
      <ConfirmDialog open={showConfirm} title="Delete Group" message={<>Delete &quot;<b>{group.name}</b>&quot;? Underlying keyword trackers will stay intact.</>} confirmLabel="Delete" loading={deleting} onConfirm={handleDelete} onCancel={() => setShowConfirm(false)} />
    </div>
  )
}

const ManageKeywordsModal = ({ group, keywordTrackers, onClose, onUpdate }: { group: KeywordGroup; keywordTrackers: KeywordTracker[]; onClose: () => void; onUpdate: (group: KeywordGroup) => void }) => {
  const [items, setItems] = useState<TrackedKeywordInput[]>(group.tracked_keywords.map(k => ({ tracker_code: k.tracker_code, enabled: k.enabled })))
  const [selectedToAdd, setSelectedToAdd] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const trackerByCode = useMemo(() => new Map(keywordTrackers.map(t => [t.tracker_code, t])), [keywordTrackers])
  const available = keywordTrackers.filter(t => (t.marketplace ?? group.marketplace) === group.marketplace && !items.some(i => i.tracker_code === t.tracker_code))

  const addKeyword = () => { if (!selectedToAdd) return; setItems(prev => [...prev, { tracker_code: selectedToAdd, enabled: true }]); setSelectedToAdd(""); setError(null) }
  const removeKeyword = (code: string) => setItems(prev => prev.filter(i => i.tracker_code !== code))
  const toggleKeyword = (code: string) => setItems(prev => prev.map(i => i.tracker_code === code ? { ...i, enabled: !i.enabled } : i))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (items.length === 0) { setError("At least one keyword tracker is required."); return }
    setSubmitting(true)
    try { onUpdate(await apiReplaceTrackedKeywords(group.group_code, items)) }
    catch (err) { handleApiError(err, setError, "Duplicate keyword tracker in group.", "Failed to update grouped keywords."); setSubmitting(false) }
  }

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)", zIndex: 1000, overflowY: "auto" }}>
      <div style={{ minHeight: "100%", display: "flex", alignItems: "flex-start", justifyContent: "center", padding: "72px 24px 24px" }}>
        <div className="card" style={{ width: "100%", maxWidth: 620, padding: "24px 28px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
            <div><span style={{ fontSize: 16, fontWeight: 700, color: T.text0 }}>Manage Keywords</span><div style={{ fontSize: 11, color: T.text3, marginTop: 2 }}>{group.name}</div></div>
            <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: T.text3, display: "flex" }}><X size={18} /></button>
          </div>
          <form onSubmit={handleSubmit}>
            <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
              <select value={selectedToAdd} onChange={e => setSelectedToAdd(e.target.value)} className="input" style={{ flex: 1 }}>
                <option value="">Select keyword tracker...</option>
                {available.map(t => <option key={t.tracker_code} value={t.tracker_code}>{keywordLabel(t)}</option>)}
              </select>
              <button type="button" onClick={addKeyword} className="btn-ghost" style={{ display: "flex", alignItems: "center", gap: 6 }}><Plus size={13} /> Add</button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16, maxHeight: 260, overflowY: "auto" }}>
              {items.map(item => {
                const tracker = trackerByCode.get(item.tracker_code)
                return <div key={item.tracker_code} style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 12px", border: `1px solid ${item.enabled ? T.border2 : T.border}`, borderRadius: 8, background: item.enabled ? T.bg3 : T.bg2, opacity: item.enabled ? 1 : 0.65 }}>
                  <input type="checkbox" checked={item.enabled} onChange={() => toggleKeyword(item.tracker_code)} />
                  <div style={{ flex: 1, minWidth: 0 }}><div style={{ fontSize: 12, color: T.text0, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{tracker?.name ?? item.tracker_code}</div><div style={{ fontSize: 11, color: T.text3, marginTop: 2 }}>{tracker ? `"${tracker.scope.keyword}"` : item.tracker_code}</div></div>
                  <button type="button" onClick={() => removeKeyword(item.tracker_code)} style={{ background: "none", border: "none", color: T.red, cursor: "pointer", display: "flex" }}><Trash2 size={14} /></button>
                </div>
              })}
            </div>
            {error && <ErrorBanner message={error} />}
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}><button type="button" className="btn-ghost" onClick={onClose}>Cancel</button><button type="submit" className="btn-primary" disabled={submitting}>{submitting ? "Saving..." : "Save Keywords"}</button></div>
          </form>
        </div>
      </div>
    </div>
  )
}

type KpiFilter = "ALL" | "UP" | "DOWN" | "NEW" | "STABLE" | "NEW_ENTRANTS" | "RETURNING" | "EXITS" | "ENTER_TOP10" | "EXIT_TOP10"

const TREND_FILTERS = new Set<KpiFilter>(["UP", "DOWN", "NEW", "STABLE"])

const KeywordDetailPanel = ({
  group,
  keywordTrackers,
  selectedKeyword,
}: {
  group: KeywordGroup
  keywordTrackers: KeywordTracker[]
  selectedKeyword: TrackedKeyword
}) => {
  const [timeframe, setTimeframe] = useState<Timeframe>("WEEKLY")
  const [snapshot, setSnapshot] = useState<CategorySnapshot | null>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [activeKpiFilter, setActiveKpiFilter] = useState<KpiFilter>("ALL")
  const [openCouponKey, setOpenCouponKey] = useState<string | null>(null)
  const [openDealKey, setOpenDealKey] = useState<string | null>(null)
  const [showMetaDetail, setShowMetaDetail] = useState(false)

  const tracker = keywordTrackers.find(t => t.tracker_code === selectedKeyword.tracker_code)

  useEffect(() => {
    let cancelled = false
    apiGetLatestKeywordSnapshot(selectedKeyword.tracker_code, timeframe)
      .then(snap => { if (!cancelled) setSnapshot(snap) })
      .catch(() => { if (!cancelled) setSnapshot(null) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [selectedKeyword.tracker_code, timeframe])

  const products = useMemo(() => {
    if (!snapshot) return []
    const q = search.trim().toLowerCase()
    const searched = q
      ? snapshot.products.filter(product => [product.asin, product.title, product.brand].some(value => value.toLowerCase().includes(q)))
      : snapshot.products
    if (activeKpiFilter === "ALL") return searched
    if (TREND_FILTERS.has(activeKpiFilter)) return searched.filter(product => product.rank_trend === activeKpiFilter)
    if (activeKpiFilter === "NEW_ENTRANTS") return searched.filter(product => product.rank_trend === "NEW")
    if (activeKpiFilter === "ENTER_TOP10") return searched.filter(product => product.rank_position <= 10 && (product.previous_rank_position == null || product.previous_rank_position > 10))
    if (activeKpiFilter === "EXIT_TOP10") return []
    return []
  }, [snapshot, search, activeKpiFilter])

  const totalFilteredCount = useMemo(() => {
    if (!snapshot) return 0
    if (activeKpiFilter === "ALL") return snapshot.products.length
    if (TREND_FILTERS.has(activeKpiFilter)) return snapshot.products.filter(product => product.rank_trend === activeKpiFilter).length
    if (activeKpiFilter === "NEW_ENTRANTS") return snapshot.summary.new_entrant_count
    if (activeKpiFilter === "RETURNING") return snapshot.summary.returning_count
    if (activeKpiFilter === "EXITS") return snapshot.summary.exit_count
    if (activeKpiFilter === "ENTER_TOP10") return snapshot.summary.enter_top10_count
    if (activeKpiFilter === "EXIT_TOP10") return snapshot.summary.exit_top10_count
    return 0
  }, [snapshot, activeKpiFilter])

  const rows = products.map(product => ({ kind: "product" as const, key: `${product.asin}-${product.rank_position}`, product }))

  return (
    <div className="anim-slide">
      <TrackerInfoCard
        name={tracker?.name ?? selectedKeyword.tracker_name_snapshot}
        marketplace={group.marketplace}
        status={tracker?.status ?? group.status}
        meta={`"${tracker?.scope.keyword ?? selectedKeyword.keyword_snapshot}" - Top ${tracker?.tracking_config.top_n ?? 50} - Daily at ${String(tracker?.schedule.hour_utc ?? 2).padStart(2, "0")}:00 UTC`}
        statsRight={
          <>
            {(tracker?.stats.last_success_at || selectedKeyword.added_at) && (
              <TrackerStat label="Last capture" value={new Date(tracker?.stats.last_success_at ?? selectedKeyword.added_at).toLocaleDateString()} />
            )}
            <TrackerStat label="Snapshots" value={tracker?.stats.snapshot_count ?? "-"} />
          </>
        }
      />

      {snapshot && (
        <SnapshotMetadataBar
          snapshotDate={snapshot.snapshot_date}
          capturedAt={snapshot.captured_at}
          sourceRefs={
            (snapshot.source_refs?.provider || snapshot.source_refs?.apify_run_id) ? (
              <span style={{ position: "relative", display: "inline-flex" }}>
                <button type="button" onClick={() => setShowMetaDetail(v => !v)}
                  style={{ background: "none", border: "none", cursor: "pointer", color: T.text3, display: "inline-flex", alignItems: "center", gap: 3, padding: "2px 4px", borderRadius: 4 }}>
                  Details
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

      {snapshot && (
        <KpiFilterBar
          summary={{
            asin_count: snapshot.summary.asin_count,
            new_entrants: snapshot.summary.new_entrant_count,
            returning: snapshot.summary.returning_count,
            exits: snapshot.summary.exit_count,
            enter_top10: snapshot.summary.enter_top10_count,
            exit_top10: snapshot.summary.exit_top10_count,
            up: snapshot.products.filter(product => product.rank_trend === "UP").length,
            down: snapshot.products.filter(product => product.rank_trend === "DOWN").length,
            new: snapshot.products.filter(product => product.rank_trend === "NEW").length,
            stable: snapshot.products.filter(product => product.rank_trend === "STABLE").length,
          }}
          activeFilter={activeKpiFilter}
          onFilterChange={filter => setActiveKpiFilter(filter as KpiFilter)}
        />
      )}

      <ProductTable
        search={search}
        onSearchChange={setSearch}
        allVisibleRows={rows}
        totalFilteredCount={totalFilteredCount}
        activeKpiFilter={activeKpiFilter}
        loading={loading}
        openCouponKey={openCouponKey}
        openDealKey={openDealKey}
        onOpenCouponKeyChange={setOpenCouponKey}
        onOpenDealKeyChange={setOpenDealKey}
        justAdded={null}
        triggering={false}
        onTrigger={() => undefined}
        hasSnapshot={!!snapshot}
        productUrlResolver={(product) => product.product_url || `https://www.amazon.com/dp/${product.asin}`}
        headerExtra={
          <div style={{ display: "flex", gap: 4 }}>
            {(["WEEKLY", "MONTHLY"] as Timeframe[]).map(item => (
              <button key={item} onClick={() => setTimeframe(item)}
                style={{ padding: "5px 10px", borderRadius: 6, border: `1px solid ${item === timeframe ? T.amber : T.border}`, background: item === timeframe ? T.bg4 : "transparent", color: item === timeframe ? T.amber : T.text3, fontSize: 11, fontWeight: 600, cursor: "pointer" }}>
                {item === "WEEKLY" ? "7 days" : "30 days"}
              </button>
            ))}
          </div>
        }
      />
    </div>
  )
}

const KeywordGroupSnapshotTable = ({
  group,
  keywordTrackers,
  snapshot,
  loading,
}: {
  group: KeywordGroup | null
  keywordTrackers: KeywordTracker[]
  snapshot: KeywordGroupSnapshot | null
  loading: boolean
}) => {
  const [selectedKeywordCode, setSelectedKeywordCode] = useState("")

  const keywords = useMemo(() => group?.tracked_keywords.filter(keyword => keyword.enabled) ?? [], [group])
  const selectedKeyword = keywords.find(keyword => keyword.tracker_code === selectedKeywordCode) ?? keywords[0]


  const renderKeywordLayout = () => {
    if (!group) return null
    return (
      <div style={{ display: "grid", gridTemplateColumns: "280px minmax(0, 1fr)", gap: 16, padding: 14, overflowX: "auto" }}>
        <div>
          <div style={{ fontSize: 10, fontWeight: 600, color: T.text3, letterSpacing: ".08em", textTransform: "uppercase", marginBottom: 8, padding: "0 4px" }}>
            {keywords.length} keywords in group
          </div>
          <div style={{ maxHeight: 680, overflowY: "auto", paddingRight: 4 }}>
            {keywords.map(keyword => {
              const tracker = keywordTrackers.find(item => item.tracker_code === keyword.tracker_code)
              const summary = snapshot?.keyword_summaries.find(item => item.tracker_code === keyword.tracker_code)
              const isSelected = keyword.tracker_code === (selectedKeyword?.tracker_code ?? "")
              return (
                <div key={keyword.tracker_code} className="row-hover" onClick={() => setSelectedKeywordCode(keyword.tracker_code)}
                  style={{ padding: "10px 12px", borderRadius: 8, marginBottom: 4, background: isSelected ? T.bg4 : T.bg2, border: `1px solid ${isSelected ? T.border2 : T.border}`, cursor: "pointer", transition: "all .15s" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 4 }}>
                    <span style={{ fontSize: 12, color: T.text0, fontWeight: 700, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{keyword.keyword_snapshot}</span>
                    <span style={{ fontSize: 10, fontFamily: T.mono, color: T.amber }}>{summary?.asin_count ?? tracker?.latest_snapshot_summary?.top10_asins.length ?? "-"} ASINs</span>
                  </div>
                  <div style={{ fontSize: 11, color: T.text2, marginBottom: 5, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{keyword.tracker_name_snapshot}</div>
                  <div style={{ fontSize: 10, fontFamily: T.mono, color: T.text3 }}>{keyword.tracker_code}</div>
                </div>
              )
            })}
          </div>
        </div>
        <div style={{ minWidth: 0 }}>
          {selectedKeyword ? (
            <KeywordDetailPanel group={group} keywordTrackers={keywordTrackers} selectedKeyword={selectedKeyword} />
          ) : (
            <div className="card" style={{ textAlign: "center", padding: 40, color: T.text3 }}>No keyword selected</div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="card" style={{ padding: 0, overflow: "visible" }}>
      <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}`, display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: T.text1 }}>Keyword tracker detail</div>
        <span style={{ fontSize: 11, color: T.text3, fontFamily: T.mono, marginLeft: "auto" }}>{keywords.length} keywords</span>
      </div>
      {loading ? (
        <div style={{ textAlign: "center", padding: 40, color: T.text3 }}>Loading group snapshot...</div>
      ) : !group ? (
        <div style={{ textAlign: "center", padding: 46, color: T.text3 }}><AlertCircle size={22} style={{ marginBottom: 8, opacity: 0.5 }} /><br />No keyword group selected.</div>
      ) : renderKeywordLayout()}
    </div>
  )
}
export const KeywordGroupsPanel = () => {
  const [groups, setGroups] = useState<KeywordGroup[]>([])
  const [keywordTrackers, setKeywordTrackers] = useState<KeywordTracker[]>([])
  const [selectedCode, setSelectedCode] = useState("")
  const [statusFilter, setStatusFilter] = useState("ACTIVE")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [snapshot, setSnapshot] = useState<KeywordGroupSnapshot | null>(null)
  const [snapshotLoading, setSnapshotLoading] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [showEdit, setShowEdit] = useState(false)
  const [showManage, setShowManage] = useState(false)

  useEffect(() => {
    let cancelled = false
    Promise.all([apiListKeywordGroups(1, 200), apiListKeywordTrackers(1, 200)]).then(([groupRes, trackerRes]) => {
      if (cancelled) return
      setGroups(groupRes.items)
      setKeywordTrackers(trackerRes.items)
      const first = groupRes.items.find(g => g.status === "ACTIVE") ?? groupRes.items[0]
      setSelectedCode(first?.group_code ?? "")
    }).catch(() => setError("Failed to load keyword groups")).finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    if (!selectedCode) return
    let cancelled = false
    apiGetLatestKeywordGroupSnapshot(selectedCode).then(snap => { if (!cancelled) setSnapshot(snap) }).catch(() => { if (!cancelled) setSnapshot(null) }).finally(() => { if (!cancelled) setSnapshotLoading(false) })
    return () => { cancelled = true }
  }, [selectedCode])

  const selectedGroup = groups.find(g => g.group_code === selectedCode)
  const selectorGroups = groups.map(groupToSelector)

  const handleCreate = (group: KeywordGroup) => { setGroups(prev => [group, ...prev]); setSnapshotLoading(true); setSelectedCode(group.group_code); setShowCreate(false) }
  const handleUpdate = (group: KeywordGroup) => {
    setGroups(prev => prev.map(item => item.group_code === group.group_code ? group : item))
    setShowEdit(false)
    setShowManage(false)
    if (group.group_code === selectedCode) {
      setSnapshotLoading(true)
      apiGetLatestKeywordGroupSnapshot(group.group_code).then(setSnapshot).catch(() => setSnapshot(null)).finally(() => setSnapshotLoading(false))
    }
  }
  const handleDelete = (groupCode: string) => { const remaining = groups.filter(g => g.group_code !== groupCode); setGroups(remaining); setSelectedCode(remaining[0]?.group_code ?? ""); if (remaining.length === 0) setSnapshot(null); setShowEdit(false) }

  if (groups.length === 0) return <>{showCreate && <CreateKeywordGroupModal keywordTrackers={keywordTrackers} onClose={() => setShowCreate(false)} onCreate={handleCreate} />}<div className="card" style={{ textAlign: "center", padding: "80px 24px", color: T.text3 }}>{loading ? <div style={{ fontSize: 13 }}>Loading groups...</div> : <><Layers3 size={40} style={{ margin: "0 auto 16px", opacity: 0.3 }} /><div style={{ fontSize: 15, fontWeight: 600, color: T.text1, marginBottom: 6 }}>No keyword groups yet</div><div style={{ fontSize: 12, color: error ? T.red : T.text3, marginBottom: 24 }}>{error ?? "Group keyword trackers to compare product overlap across searches."}</div><button className="btn-primary" onClick={() => setShowCreate(true)} style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12 }}><Plus size={14} /> New Group</button></>}</div></>

  return (
    <div className="anim-fade">
      {showCreate && <CreateKeywordGroupModal keywordTrackers={keywordTrackers} onClose={() => setShowCreate(false)} onCreate={handleCreate} />}
      {showEdit && selectedGroup && <EditKeywordGroupModal group={selectedGroup} onClose={() => setShowEdit(false)} onUpdate={handleUpdate} onDelete={handleDelete} />}
      {showManage && selectedGroup && <ManageKeywordsModal group={selectedGroup} keywordTrackers={keywordTrackers} onClose={() => setShowManage(false)} onUpdate={handleUpdate} />}
      <PageHeader title="Keyword Groups" sub="Aggregate products across multiple keyword trackers" />
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, marginTop: -12, marginBottom: 14, flexWrap: "wrap" }}>
        <div style={{ fontSize: 11, color: T.text3, fontFamily: T.mono }}>
          {selectedGroup ? selectedGroup.group_code : "No group selected"}
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          {selectedGroup && (
            <>
              <button className="btn-ghost" onClick={() => setShowManage(true)}
                style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12, padding: "8px 10px", whiteSpace: "nowrap" }}>
                <Settings size={14} /> Manage Keywords
              </button>
              <button className="btn-ghost" onClick={() => setShowEdit(true)}
                style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12, padding: "8px 10px", whiteSpace: "nowrap" }}>
                <Edit2 size={14} /> Edit Group
              </button>
            </>
          )}
          <button className="btn-primary" onClick={() => setShowCreate(true)}
            style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12, padding: "8px 11px", whiteSpace: "nowrap" }}>
            <Plus size={14} /> New Group
          </button>
        </div>
      </div>
      {error && <ErrorBanner message={error} />}
      <StatusFilterTabs trackers={selectorGroups} value={statusFilter} onChange={setStatusFilter} />
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        {groups.filter(group => (group.status ?? "ACTIVE") === statusFilter).map(group => {
          const isSelected = group.group_code === selectedCode
          const sc = statusColor(group.status)
          return (
            <button key={group.group_code} onClick={() => { setSnapshotLoading(true); setSelectedCode(group.group_code) }}
              style={{ padding: "7px 14px", borderRadius: 8, border: `1px solid ${isSelected ? sc : T.border}`, background: isSelected ? T.bg4 : T.bg2, color: isSelected ? sc : T.text1, fontSize: 13, fontFamily: T.sans, cursor: "pointer", transition: "all .15s", display: "flex", alignItems: "center", gap: 6 }}>
              {isSelected && <span className="dot-live" style={{ background: sc, boxShadow: `0 0 0 3px ${sc}30` }} />}
              {group.name}
              <span style={{ fontSize: 10, fontFamily: T.mono, color: T.text3 }}>({group.marketplace})</span>
            </button>
          )
        })}
      </div>
      {selectedGroup && <TrackerInfoCard name={selectedGroup.name} marketplace={selectedGroup.marketplace} status={selectedGroup.status} meta={`${selectedGroup.tracked_keywords.filter(k => k.enabled).length} active keywords - ${selectedGroup.tracked_keywords.length} total`} statsRight={<><TrackerStat label="Unique ASINs" value={selectedGroup.latest_snapshot_summary?.total_unique_asins ?? snapshot?.total_unique_asins ?? "-"} /><TrackerStat label="Snapshots" value={selectedGroup.stats.total_snapshots_covered} /></>}><div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>{selectedGroup.tracked_keywords.slice(0, 8).map(keyword => <span key={keyword.tracker_code} style={{ padding: "3px 7px", borderRadius: 5, border: `1px solid ${keyword.enabled ? T.border2 : T.border}`, background: keyword.enabled ? T.bg4 : T.bg3, color: keyword.enabled ? T.text2 : T.text3, fontSize: 10 }}>{keyword.keyword_snapshot}{!keyword.enabled ? " - off" : ""}</span>)}{selectedGroup.tracked_keywords.length > 8 && <span style={{ color: T.text3, fontSize: 10, padding: "3px 0" }}>+{selectedGroup.tracked_keywords.length - 8}</span>}</div></TrackerInfoCard>}
      {snapshot && <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 10, marginBottom: 16 }}>{[["Unique ASINs", snapshot.total_unique_asins], ["Keywords", snapshot.keyword_count], ["Overlap", snapshot.products.filter(p => p.keyword_count > 1).length], ["Captured", new Date(snapshot.captured_at).toLocaleDateString()]].map(([label, value]) => <div key={label} className="card" style={{ padding: "12px 14px" }}><div style={{ fontSize: 11, color: T.text3, marginBottom: 4 }}>{label}</div><div style={{ fontSize: 18, color: T.text0, fontWeight: 700, fontFamily: T.mono }}>{value}</div></div>)}</div>}
      <KeywordGroupSnapshotTable group={selectedGroup ?? null} keywordTrackers={keywordTrackers} snapshot={snapshot} loading={snapshotLoading} />
    </div>
  )
}





























