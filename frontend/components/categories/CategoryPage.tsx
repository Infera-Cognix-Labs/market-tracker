"use client"

import { useState, useEffect, useMemo } from "react"
import { Search, TrendingUp, TrendingDown, Star, Zap, RefreshCw, ExternalLink, Plus, Edit2, X, CheckCircle, AlertCircle } from "lucide-react"
import { T } from "../shared/DesignTokens"
import { PageHeader } from "../shared/PageHeader"
import { Badge } from "../shared/Badge"
import { apiListCategoryTrackers, apiGetLatestCategorySnapshot, apiCreateCategoryTracker, apiUpdateCategoryTracker } from "../shared/api"
import type { CategoryTracker, CategorySnapshot, CategorySnapshotProduct, CategoryTrackerCreateRequest, CategoryTrackerUpdateRequest, TrackerStatus } from "../shared/types"

// ── Helpers ───────────────────────────────────────────────────────────────────
function parseNodeId(input: string): string | null {
  const trimmed = input.trim()
  if (/^\d+$/.test(trimmed)) return trimmed
  const pathMatch = trimmed.match(/\/zgbs\/[^/]+\/(\d+)/)
  if (pathMatch) return pathMatch[1]
  const queryMatch = trimmed.match(/[?&]node=(\d+)/)
  if (queryMatch) return queryMatch[1]
  return null
}

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

// ── Create Category Tracker Modal ─────────────────────────────────────────────
interface CreateModalProps { onClose: () => void; onCreate: (t: CategoryTracker) => void }

const CreateCategoryTrackerModal = ({ onClose, onCreate }: CreateModalProps) => {
  const [nodeInput, setNodeInput] = useState("")
  const [name, setName] = useState("")
  const [marketplace, setMarketplace] = useState("amazon_us")
  const [top10Alert, setTop10Alert] = useState(true)
  const [hourUtc, setHourUtc] = useState(2)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const parsedNodeId = parseNodeId(nodeInput)
  const isUrl = nodeInput.trim().startsWith("http")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!nodeInput.trim()) { setError("Please enter a browse node ID or URL."); return }
    if (!name.trim()) { setError("Please enter a tracker name."); return }
    const scope = isUrl
      ? { browse_node_url: nodeInput.trim(), browse_node_id: parsedNodeId ?? undefined }
      : { browse_node_id: nodeInput.trim() }
    const payload: CategoryTrackerCreateRequest = {
      name: name.trim(), marketplace, scope,
      tracking_config: { top10_alert_enabled: top10Alert },
      schedule: { frequency: "DAILY", hour_utc: hourUtc },
    }
    setSubmitting(true)
    try {
      const tracker = await apiCreateCategoryTracker(payload)
      onCreate(tracker)
    } catch {
      setError("Failed to create tracker. Please try again.")
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
            <label style={labelStyle}>Browse Node ID or Best-sellers URL</label>
            <div style={{ position: "relative" }}>
              <Search size={13} style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)", color: T.text3, pointerEvents: "none" }} />
              <input type="text" value={nodeInput} onChange={e => setNodeInput(e.target.value)}
                placeholder="e.g. 13893610011 or https://www.amazon.com/Best-Sellers/zgbs/..."
                style={{ ...inputStyle, paddingLeft: 32 }} />
            </div>
            {nodeInput.trim() && (
              <div style={{ marginTop: 5, display: "flex", alignItems: "center", gap: 6 }}>
                {parsedNodeId
                  ? <><CheckCircle size={12} style={{ color: T.green }} /><span style={{ fontSize: 11, color: T.green, fontFamily: T.mono }}>Node ID: {parsedNodeId}</span></>
                  : <><AlertCircle size={12} style={{ color: T.red }} /><span style={{ fontSize: 11, color: T.red }}>Could not extract node ID — check URL format</span></>
                }
                {isUrl && (
                  <a href={nodeInput.trim()} target="_blank" rel="noopener noreferrer"
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
            <label style={labelStyle}>Marketplace</label>
            <select value={marketplace} onChange={e => setMarketplace(e.target.value)} style={{ ...inputStyle, cursor: "pointer" }}>
              {MARKETPLACES.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
            </select>
          </div>
          <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
            <div style={{ flex: 1 }}>
              <label style={labelStyle}>Run at (UTC hour)</label>
              <select value={hourUtc} onChange={e => setHourUtc(Number(e.target.value))} style={{ ...inputStyle, cursor: "pointer" }}>
                {Array.from({ length: 24 }, (_, i) => <option key={i} value={i}>{String(i).padStart(2, "0")}:00 UTC</option>)}
              </select>
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
interface EditModalProps { tracker: CategoryTracker; onClose: () => void; onUpdate: (t: CategoryTracker) => void }

const EditCategoryTrackerModal = ({ tracker, onClose, onUpdate }: EditModalProps) => {
  const [name, setName] = useState(tracker.name)
  const [top10Alert, setTop10Alert] = useState(tracker.tracking_config.top10_alert_enabled)
  const [hourUtc, setHourUtc] = useState(tracker.schedule.hour_utc)
  const [status, setStatus] = useState<TrackerStatus>(tracker.status as TrackerStatus)
  const [submitting, setSubmitting] = useState(false)
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
              <label style={labelStyle}>Run at (UTC hour)</label>
              <select value={hourUtc} onChange={e => setHourUtc(Number(e.target.value))} style={{ ...inputStyle, cursor: "pointer" }}>
                {Array.from({ length: 24 }, (_, i) => <option key={i} value={i}>{String(i).padStart(2, "0")}:00 UTC</option>)}
              </select>
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

export const CategoryPage = () => {
  const [trackers, setTrackers] = useState<CategoryTracker[]>([])
  const [selectedCode, setSelectedCode] = useState<string>("")
  const [snapshot, setSnapshot] = useState<CategorySnapshot | null>(null)
  const [search, setSearch] = useState("")
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [showEdit, setShowEdit] = useState(false)

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
    let cancelled = false
    apiGetLatestCategorySnapshot(selectedCode)
      .then(snap => { if (!cancelled) { setSnapshot(snap); setLoading(false) } })
      .catch(() => { if (!cancelled) { setSnapshot(null); setLoading(false) } })
    return () => { cancelled = true }
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
    <>
      {showCreate && (
        <CreateCategoryTrackerModal
          onClose={() => setShowCreate(false)}
          onCreate={t => { setTrackers(prev => [t, ...prev]); setSelectedCode(t.tracker_code); setShowCreate(false) }}
        />
      )}
      {showEdit && selectedTracker && (
        <EditCategoryTrackerModal
          tracker={selectedTracker}
          onClose={() => setShowEdit(false)}
          onUpdate={t => { setTrackers(prev => prev.map(x => x.tracker_code === t.tracker_code ? t : x)); setShowEdit(false) }}
        />
      )}
    <div className="anim-fade">
      <PageHeader title="Category Tracker" sub="Top 50 BSR — Daily snapshots from normalized data"
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

      {/* Tracker selector tabs */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        {trackers.map(t => (
          <button key={t.tracker_code} onClick={() => { setSnapshot(null); setLoading(true); setSelectedCode(t.tracker_code) }}
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
        <div style={{ display: "flex", gap: 12, marginBottom: 8, fontSize: 11, color: T.text3, fontFamily: T.mono, flexWrap: "wrap" }}>
          <span>Snapshot: {snapshot.snapshot_date}</span>
          <span>Captured: {new Date(snapshot.captured_at).toLocaleString()}</span>
          {snapshot.source_refs?.provider && <span>Provider: {snapshot.source_refs.provider}</span>}
          {snapshot.source_refs?.apify_run_id && <span>Run: {snapshot.source_refs.apify_run_id}</span>}
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
                {["#", "Img", "ASIN", "Title", "Brand", "Price", "Rating", "Reviews", "Availability", "Buy Box", "Coupon"].map(h => (
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
                  <td style={{ padding: "9px 10px", fontSize: 11, color: T.text2 }}>{p.brand}</td>
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
                  <td style={{ padding: "9px 10px" }}>
                    <Badge type={p.buy_box_status === "HAS_BUY_BOX" ? "listing" : p.buy_box_status === "NO_BUY_BOX" ? "stock" : "info"} text={p.buy_box_status === "HAS_BUY_BOX" ? "Has BB" : p.buy_box_status === "NO_BUY_BOX" ? "No BB" : "—"} />
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
    </>
  )
}
