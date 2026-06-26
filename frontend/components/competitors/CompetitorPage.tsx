"use client"

import { AlertCircle, CheckCircle, Edit2, ExternalLink, Package, Plus, Settings, Trash2, X } from "lucide-react"
import { useEffect, useState } from "react"
import { CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { AlertTypeMeta } from "../shared/AlertTypeMeta"
import { Badge } from "../shared/Badge"
import { ConfirmDialog } from "../shared/ConfirmDialog"
import { T, statusColor } from "../shared/DesignTokens"
import { Dropdown } from "../shared/Dropdown"
import { PageHeader } from "../shared/PageHeader"
import { StatusFilterTabs } from "../shared/StatusFilterTabs"
import { TrackerInfoCard, TrackerStat } from "../shared/TrackerInfoCard"
import { apiCreateCompetitorTracker, apiDeleteCompetitorTracker, apiGetCompetitorTracker, apiGetProductDetail, apiGetProductTimeline, apiListCompetitorTrackers, apiListEvents, apiReplaceTrackedAsins, apiUpdateCompetitorTracker } from "../shared/api"
import { MARKETPLACES, parseCouponItems, parseDealItems, HOURS as SHARED_HOURS } from "../shared/formatting"
import { ExpandableList } from "../shared/ExpandableList"
import { handleApiError } from "../shared/hooks"
import { ThumbnailImage } from "../shared/ThumbnailImage"
import type { CompetitorTrackerCreateRequest, CompetitorTrackerDetail, CompetitorTrackerUpdateRequest, CompetitorTrackFields, Event, ProductDetail, ProductTimelineResponse, Timeframe, TrackedProductSummary, TrackerStatus } from "../shared/types"

const HOURS = SHARED_HOURS

const DEFAULT_TRACK_FIELDS: CompetitorTrackFields = {
  bsr: true, price: true, buy_box: true, availability: true,
  promotions: true, title_change: true, main_image_change: true,
  variation_change: true, content_change: true,
}

const TRACK_FIELD_LABELS: Record<keyof CompetitorTrackFields, string> = {
  bsr: "BSR", price: "Price", buy_box: "Buy Box", availability: "Availability",
  promotions: "Promotions", title_change: "Title Change", main_image_change: "Image Change",
  variation_change: "Variation Change", content_change: "Content Change",
}

const validNumbers = (values: Array<number | null | undefined>) =>
  values.filter((value): value is number => Number.isFinite(value))

const paddedDomain = (
  values: Array<number | null | undefined>,
  options: { paddingRatio?: number; minSpan?: number; floor?: number; ceil?: number } = {}
): [number, number] | undefined => {
  const nums = validNumbers(values)
  if (nums.length === 0) return undefined

  const min = Math.min(...nums)
  const max = Math.max(...nums)
  const minSpan = options.minSpan ?? 1
  const span = Math.max(max - min, minSpan)
  const padding = span * (options.paddingRatio ?? 0.12)
  const lower = Math.max(options.floor ?? -Infinity, min - padding)
  const upper = Math.min(options.ceil ?? Infinity, max + padding)

  return [lower, upper]
}

const paddedIntegerDomain = (
  values: Array<number | null | undefined>,
  options: { paddingRatio?: number; minSpan?: number; floor?: number } = {}
): [number, number] | undefined => {
  const domain = paddedDomain(values, options)
  if (!domain) return undefined
  return [
    Math.max(options.floor ?? -Infinity, Math.floor(domain[0])),
    Math.ceil(domain[1]),
  ]
}

const formatCompactNumber = (value: number) => {
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}m`
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(value >= 10_000 ? 0 : 1)}k`
  return Math.round(value).toLocaleString()
}
const formatMoneyAxisTick = (value: number, symbol: string, domain?: [number, number]) => {
  const range = domain ? Math.abs(domain[1] - domain[0]) : 0
  const decimals = range > 0 && range < 2 ? 2 : range > 0 && range < 10 ? 1 : 0
  return `${symbol}${Number(value).toFixed(decimals)}`
}


// ── Manage ASINs Modal ────────────────────────────────────────────────────────
const ManageAsinsModal = ({
  tracker,
  onClose,
  onUpdate,
}: {
  tracker: CompetitorTrackerDetail
  onClose: () => void
  onUpdate: (updated: CompetitorTrackerDetail) => void
}) => {
  const [asins, setAsins] = useState<{ asin: string; enabled: boolean }[]>(
    tracker.tracked_asins.map(a => ({ asin: a.asin, enabled: a.enabled }))
  )
  const [asinInput, setAsinInput] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const addAsin = () => {
    const raw = asinInput.trim().toUpperCase()
    if (!raw) return
    if (!/^[A-Z0-9]{10}$/.test(raw)) { setError("Invalid ASIN — must be 10 alphanumeric characters."); return }
    if (asins.some(a => a.asin === raw)) { setError("ASIN already in list."); return }
    if (asins.length >= 200) { setError("Maximum 200 ASINs per tracker."); return }
    setAsins(prev => [...prev, { asin: raw, enabled: true }])
    setAsinInput("")
    setError(null)
  }

  const removeAsin = (asin: string) => setAsins(prev => prev.filter(a => a.asin !== asin))
  const toggleAsin = (asin: string) =>
    setAsins(prev => prev.map(a => a.asin === asin ? { ...a, enabled: !a.enabled } : a))

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (asins.length === 0) { setError("At least one ASIN is required."); return }
    setSubmitting(true)
    try {
      const updated = await apiReplaceTrackedAsins(
        tracker.tracker_code,
        asins.map(({ asin, enabled }) => ({ asin, enabled }))
      )
      onUpdate(updated)
    } catch {
      setError("Failed to update ASINs. Please try again.")
      setSubmitting(false)
    }
  }

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(7,9,15,.75)", zIndex: 1000, overflowY: "auto" }}>
      <div style={{ minHeight: "100%", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
        <div style={{ background: T.bg2, border: `1px solid ${T.border}`, borderRadius: 12, width: "100%", maxWidth: 480 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "18px 20px", borderBottom: `1px solid ${T.border}` }}>
            <div>
              <span style={{ fontSize: 15, fontWeight: 700, color: T.text0 }}>Manage ASINs</span>
              <div style={{ fontSize: 11, color: T.text3, marginTop: 2 }}>{tracker.name}</div>
            </div>
            <button onClick={onClose} style={{ background: "none", border: "none", color: T.text2, cursor: "pointer", padding: 4, display: "flex" }}><X size={16} /></button>
          </div>
          <form onSubmit={handleSave} style={{ padding: "20px" }}>
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: "block", fontSize: 11, fontWeight: 600, color: T.text2, marginBottom: 5, letterSpacing: ".04em", textTransform: "uppercase" }}>ASINs ({asins.length}/200{asins.some(a => !a.enabled) ? ` · ${asins.filter(a => a.enabled).length} active` : ""})</label>
              <div style={{ display: "flex", gap: 8 }}>
                <input
                  type="text" value={asinInput}
                  onChange={e => { setAsinInput(e.target.value.toUpperCase()); setError(null) }}
                  onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); addAsin() } }}
                  placeholder="B0ABC12345"
                  maxLength={10}
                  className="input" style={{ fontFamily: T.mono, flex: 1 }}
                />
                <button type="button" onClick={addAsin}
                  style={{ padding: "9px 14px", borderRadius: 8, border: `1px solid ${T.border}`, background: T.bg4, color: T.text0, cursor: "pointer", fontSize: 13, fontFamily: T.sans, flexShrink: 0, display: "flex", alignItems: "center", gap: 6 }}>
                  <Plus size={13} /> Add
                </button>
              </div>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 16, maxHeight: 200, overflowY: "auto" }}>
              {asins.map(({ asin, enabled }) => (
                <span key={asin} style={{ display: "inline-flex", alignItems: "center", gap: 5, padding: "3px 8px", background: enabled ? T.bg4 : T.bg3, border: `1px solid ${enabled ? T.border2 : T.border}`, borderRadius: 6, fontSize: 11, fontFamily: T.mono, color: enabled ? T.amber : T.text3, cursor: "pointer", opacity: enabled ? 1 : 0.6 }}
                  onClick={() => toggleAsin(asin)} title={enabled ? "Click to disable" : "Click to enable"}>
                  {asin}
                  {!enabled && <span style={{ fontSize: 8, color: T.text3 }}>off</span>}
                  <button type="button" onClick={(e) => { e.stopPropagation(); removeAsin(asin) }} style={{ background: "none", border: "none", color: T.text3, cursor: "pointer", padding: 0, display: "flex", lineHeight: 1 }}><Trash2 size={10} /></button>
                </span>
              ))}
            </div>
            {error && (
              <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "9px 12px", borderRadius: 8, background: `${T.red}18`, border: `1px solid ${T.red}40`, marginBottom: 16 }}>
                <AlertCircle size={13} style={{ color: T.red, flexShrink: 0 }} />
                <span style={{ fontSize: 12, color: T.red }}>{error}</span>
              </div>
            )}
            <div style={{ display: "flex", gap: 10 }}>
              <button type="button" onClick={onClose}
                style={{ flex: 1, padding: "10px 0", borderRadius: 8, border: `1px solid ${T.border}`, background: "none", color: T.text1, fontSize: 13, fontFamily: T.sans, cursor: "pointer" }}>
                Cancel
              </button>
              <button type="submit" disabled={submitting}
                style={{ flex: 2, padding: "10px 0", borderRadius: 8, border: "none", background: submitting ? T.bg4 : `linear-gradient(135deg, ${T.amber} 0%, ${T.amberD} 100%)`, color: submitting ? T.text3 : T.bg0, fontSize: 13, fontWeight: 700, fontFamily: T.sans, cursor: submitting ? "not-allowed" : "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
                {submitting ? "Saving…" : "Save Changes"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

// ── Edit Tracker Modal ───────────────────────────────────────────────────────
const EditTrackerModal = ({
  tracker,
  onClose,
  onUpdate,
  onDelete,
}: {
  tracker: CompetitorTrackerDetail
  onClose: () => void
  onUpdate: (updated: CompetitorTrackerDetail) => void
  onDelete: (trackerCode: string) => void
}) => {
  const [name, setName] = useState(tracker.name)
  const [trackFields, setTrackFields] = useState<CompetitorTrackFields>({ ...tracker.track_fields })
  const [hourUtc, setHourUtc] = useState(tracker.schedule.hour_utc)
  const [status, setStatus] = useState<TrackerStatus>(tracker.status)
  const [submitting, setSubmitting] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const toggleField = (key: keyof CompetitorTrackFields) =>
    setTrackFields(prev => ({ ...prev, [key]: !prev[key] }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!name.trim()) { setError("Tracker name is required."); return }
    const payload: CompetitorTrackerUpdateRequest = {
      name: name.trim(),
      track_fields: trackFields,
      schedule: { frequency: "DAILY", hour_utc: hourUtc },
      status,
    }
    setSubmitting(true)
    try {
      const updated = await apiUpdateCompetitorTracker(tracker.tracker_code, payload)
      onUpdate(updated)
    } catch {
      setError("Failed to update tracker. Please try again.")
      setSubmitting(false)
    }
  }

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await apiDeleteCompetitorTracker(tracker.tracker_code)
      onDelete(tracker.tracker_code)
    } catch {
      setError("Failed to delete tracker.")
      setDeleting(false)
      setShowConfirm(false)
    }
  }

  const STATUS_OPTIONS: TrackerStatus[] = ["ACTIVE", "PAUSED", "ARCHIVED"]
  const STATUS_COLORS: Record<TrackerStatus, string> = { ACTIVE: T.green, PAUSED: T.amber, ARCHIVED: T.text3 }

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(7,9,15,.75)", zIndex: 1000, overflowY: "auto" }}>
      <div style={{ minHeight: "100%", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
        <div style={{ background: T.bg2, border: `1px solid ${T.border}`, borderRadius: 12, width: "100%", maxWidth: 500 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "18px 20px", borderBottom: `1px solid ${T.border}` }}>
            <div>
              <span style={{ fontSize: 15, fontWeight: 700, color: T.text0 }}>Edit Tracker</span>
              <div style={{ fontSize: 11, color: T.text3, marginTop: 2, fontFamily: T.mono }}>{tracker.tracker_code}</div>
            </div>
            <button onClick={onClose} style={{ background: "none", border: "none", color: T.text2, cursor: "pointer", padding: 4, display: "flex" }}><X size={16} /></button>
          </div>
          <form onSubmit={handleSubmit} style={{ padding: "20px" }}>
            {/* Name */}
            <div style={{ marginBottom: 16 }}>
              <label className="label">Tracker Name</label>
              <input type="text" value={name} onChange={e => setName(e.target.value)} maxLength={120} className="input" />
            </div>

            {/* Track fields */}
            <div style={{ marginBottom: 16 }}>
              <label className="label">Track Fields</label>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {(Object.keys(trackFields) as (keyof CompetitorTrackFields)[]).map(key => (
                  <button key={key} type="button" onClick={() => toggleField(key)}
                    style={{ padding: "5px 10px", borderRadius: 6, border: `1px solid ${trackFields[key] ? T.amber : T.border}`, background: trackFields[key] ? `${T.amber}18` : T.bg3, color: trackFields[key] ? T.amber : T.text2, fontSize: 11, fontFamily: T.sans, cursor: "pointer", transition: "all .12s" }}>
                    {trackFields[key] && <CheckCircle size={10} style={{ display: "inline", marginRight: 4 }} />}
                    {TRACK_FIELD_LABELS[key]}
                  </button>
                ))}
              </div>
            </div>

            {/* Schedule */}
            <div style={{ marginBottom: 16 }}>
              <Dropdown label="Run at (UTC hour)" value={hourUtc} onChange={v => setHourUtc(Number(v))} options={HOURS} />
            </div>

            {/* Status */}
            <div style={{ marginBottom: 20 }}>
              <label className="label">Status</label>
              <div style={{ display: "flex", gap: 8 }}>
                {STATUS_OPTIONS.map(s => (
                  <button key={s} type="button" onClick={() => setStatus(s)}
                    style={{ flex: 1, padding: "8px 0", borderRadius: 7, border: `1px solid ${s === status ? STATUS_COLORS[s] : T.border}`, background: s === status ? `${STATUS_COLORS[s]}18` : T.bg3, color: s === status ? STATUS_COLORS[s] : T.text2, fontSize: 12, fontFamily: T.sans, cursor: "pointer", fontWeight: s === status ? 700 : 400, transition: "all .12s" }}>
                    {s}
                  </button>
                ))}
              </div>
            </div>

            {error && (
              <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "9px 12px", borderRadius: 8, background: `${T.red}18`, border: `1px solid ${T.red}40`, marginBottom: 16 }}>
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
                <button type="button" onClick={onClose}
                  style={{ padding: "10px 16px", borderRadius: 8, border: `1px solid ${T.border}`, background: "none", color: T.text1, fontSize: 13, fontFamily: T.sans, cursor: "pointer" }}>
                  Cancel
                </button>
                <button type="submit" disabled={submitting}
                  style={{ padding: "10px 20px", borderRadius: 8, border: "none", background: submitting ? T.bg4 : `linear-gradient(135deg, ${T.amber} 0%, ${T.amberD} 100%)`, color: submitting ? T.text3 : T.bg0, fontSize: 13, fontWeight: 700, fontFamily: T.sans, cursor: submitting ? "not-allowed" : "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
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

// ── Create Tracker Modal ──────────────────────────────────────────────────────
const CreateTrackerModal = ({
  onClose,
  onCreate,
}: {
  onClose: () => void
  onCreate: (tracker: CompetitorTrackerDetail) => void
}) => {
  const [name, setName] = useState("")
  const [marketplace, setMarketplace] = useState("amazon_us")
  const [asinInput, setAsinInput] = useState("")
  const [asins, setAsins] = useState<string[]>([])
  const [trackFields, setTrackFields] = useState<CompetitorTrackFields>({ ...DEFAULT_TRACK_FIELDS })
  const [hourUtc, setHourUtc] = useState(3)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const addAsin = () => {
    const raw = asinInput.trim().toUpperCase()
    if (!raw) return
    if (!/^[A-Z0-9]{10}$/.test(raw)) { setError("Invalid ASIN — must be 10 alphanumeric characters."); return }
    if (asins.includes(raw)) { setError("ASIN already added."); return }
    if (asins.length >= 200) { setError("Maximum 200 ASINs per tracker."); return }
    setAsins(prev => [...prev, raw])
    setAsinInput("")
    setError(null)
  }

  const removeAsin = (asin: string) => setAsins(prev => prev.filter(a => a !== asin))

  const toggleField = (key: keyof CompetitorTrackFields) =>
    setTrackFields(prev => ({ ...prev, [key]: !prev[key] }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!name.trim()) { setError("Tracker name is required."); return }
    if (asins.length === 0) { setError("Add at least one ASIN."); return }

    const payload: CompetitorTrackerCreateRequest = {
      name: name.trim(),
      marketplace,
      tracked_asins: asins.map(asin => ({ asin, enabled: true })),
      track_fields: trackFields,
      schedule: { frequency: "DAILY", hour_utc: hourUtc },
    }
    setSubmitting(true)
    try {
      const tracker = await apiCreateCompetitorTracker(payload)
      onCreate(tracker)
    } catch (err) {
      handleApiError(err, setError, "Failed to create tracker. Please try again.")
      setSubmitting(false)
    }
  }

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(7,9,15,.75)", zIndex: 1000, overflowY: "auto" }}>
      <div style={{ minHeight: "100%", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
        <div style={{ background: T.bg2, border: `1px solid ${T.border}`, borderRadius: 12, width: "100%", maxWidth: 540 }}>
          {/* Header */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "18px 20px", borderBottom: `1px solid ${T.border}` }}>
            <span style={{ fontSize: 15, fontWeight: 700, color: T.text0 }}>New Competitor Tracker</span>
            <button onClick={onClose} style={{ background: "none", border: "none", color: T.text2, cursor: "pointer", padding: 4, display: "flex" }}><X size={16} /></button>
          </div>

          <form onSubmit={handleSubmit} style={{ padding: "20px" }}>
            {/* Name */}
            <div style={{ marginBottom: 16 }}>
              <label className="label">Tracker Name</label>
              <input type="text" value={name} onChange={e => setName(e.target.value)} maxLength={120} placeholder="e.g. Bottle Warmer Competitors - US" className="input" />
            </div>

            {/* Marketplace */}
            <div style={{ marginBottom: 16 }}>
              <Dropdown label="Marketplace" value={marketplace} onChange={v => setMarketplace(v as string)} options={MARKETPLACES} />
            </div>

            {/* ASIN input */}
            <div style={{ marginBottom: 16 }}>
              <label className="label">ASINs ({asins.length}/200)</label>
              <div style={{ display: "flex", gap: 8 }}>
                <input
                  type="text" value={asinInput}
                  onChange={e => { setAsinInput(e.target.value.toUpperCase()); setError(null) }}
                  onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); addAsin() } }}
                  placeholder="B0ABC12345"
                  maxLength={10}
                  className="input" style={{ fontFamily: T.mono, flex: 1 }}
                />
                <button type="button" onClick={addAsin}
                  style={{ padding: "9px 14px", borderRadius: 8, border: `1px solid ${T.border}`, background: T.bg4, color: T.text0, cursor: "pointer", fontSize: 13, fontFamily: T.sans, flexShrink: 0, display: "flex", alignItems: "center", gap: 6 }}>
                  <Plus size={13} /> Add
                </button>
              </div>
              {/* ASIN chips */}
              {asins.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
                  {asins.map(asin => (
                    <span key={asin} style={{ display: "inline-flex", alignItems: "center", gap: 5, padding: "3px 8px", background: T.bg4, border: `1px solid ${T.border2}`, borderRadius: 6, fontSize: 11, fontFamily: T.mono, color: T.amber }}>
                      {asin}
                      <button type="button" onClick={() => removeAsin(asin)} style={{ background: "none", border: "none", color: T.text3, cursor: "pointer", padding: 0, display: "flex", lineHeight: 1 }}><Trash2 size={10} /></button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Track fields */}
            <div style={{ marginBottom: 16 }}>
              <label className="label">Track Fields</label>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {(Object.keys(trackFields) as (keyof CompetitorTrackFields)[]).map(key => (
                  <button key={key} type="button" onClick={() => toggleField(key)}
                    style={{ padding: "5px 10px", borderRadius: 6, border: `1px solid ${trackFields[key] ? T.amber : T.border}`, background: trackFields[key] ? `${T.amber}18` : T.bg3, color: trackFields[key] ? T.amber : T.text2, fontSize: 11, fontFamily: T.sans, cursor: "pointer", transition: "all .12s" }}>
                    {trackFields[key] && <CheckCircle size={10} style={{ display: "inline", marginRight: 4 }} />}
                    {TRACK_FIELD_LABELS[key]}
                  </button>
                ))}
              </div>
            </div>

            {/* Schedule */}
            <div style={{ marginBottom: 20 }}>
              <Dropdown label="Run at (UTC hour)" value={hourUtc} onChange={v => setHourUtc(Number(v))} options={HOURS} />
            </div>

            {/* Error */}
            {error && (
              <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "9px 12px", borderRadius: 8, background: `${T.red}18`, border: `1px solid ${T.red}40`, marginBottom: 16 }}>
                <AlertCircle size={13} style={{ color: T.red, flexShrink: 0 }} />
                <span style={{ fontSize: 12, color: T.red }}>{error}</span>
              </div>
            )}

            {/* Actions */}
            <div style={{ display: "flex", gap: 10 }}>
              <button type="button" onClick={onClose}
                style={{ flex: 1, padding: "10px 0", borderRadius: 8, border: `1px solid ${T.border}`, background: "none", color: T.text1, fontSize: 13, fontFamily: T.sans, cursor: "pointer" }}>
                Cancel
              </button>
              <button type="submit" disabled={submitting}
                style={{ flex: 2, padding: "10px 0", borderRadius: 8, border: "none", background: submitting ? T.bg4 : `linear-gradient(135deg, ${T.amber} 0%, ${T.amberD} 100%)`, color: submitting ? T.text3 : T.bg0, fontSize: 13, fontWeight: 700, fontFamily: T.sans, cursor: submitting ? "not-allowed" : "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 8, transition: "all .15s" }}>
                <Plus size={14} />
                {submitting ? "Creating…" : "Create Tracker"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export const CompetitorPage = () => {
  const [trackers, setTrackers] = useState<CompetitorTrackerDetail[]>([])
  const [selectedCode, setSelectedCode] = useState<string>("")
  const [trackerDetail, setTrackerDetail] = useState<CompetitorTrackerDetail | null>(null)
  const [selectedAsinIdx, setSelectedAsinIdx] = useState(0)
  const [productDetail, setProductDetail] = useState<ProductDetail | null>(null)
  const [timeline, setTimeline] = useState<ProductTimelineResponse | null>(null)
  const [events, setEvents] = useState<Event[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingDetail, setLoadingDetail] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [showEdit, setShowEdit] = useState(false)
  const [showManageAsins, setShowManageAsins] = useState(false)
  const [chartTimeframe, setChartTimeframe] = useState<Timeframe>("DAILY")
  const [refreshKey, setRefreshKey] = useState(0)
  const [statusFilter, setStatusFilter] = useState<string>("ACTIVE")
  const [openCouponRowKey, setOpenCouponRowKey] = useState<string | null>(null)
  const [openDealRowKey, setOpenDealRowKey] = useState<string | null>(null)
  const [tablePage, setTablePage] = useState(0)
  const [eventsPage, setEventsPage] = useState(0)

  // Load tracker list only
  useEffect(() => {
    apiListCompetitorTrackers()
      .then(res => {
        setTrackers(res.items as CompetitorTrackerDetail[])
        const firstActive = (res.items as CompetitorTrackerDetail[]).find(t => (t.status ?? "ACTIVE") === "ACTIVE")
        const first = firstActive ?? res.items[0]
        if (first) setSelectedCode(first.tracker_code)
      })
      .catch(() => {
        setTrackers([])
        setError("Failed to load competitor trackers")
      })
      .finally(() => setLoading(false))
  }, [])

  // Fetch detail (tracked_products) for selected tracker
  useEffect(() => {
    if (!selectedCode) return
    let cancelled = false
    apiGetCompetitorTracker(selectedCode)
      .then(d => { if (!cancelled) { setTrackerDetail(d); setLoadingDetail(false) } })
      .catch(() => {
        if (!cancelled) {
          const fallback = trackers.find(t => t.tracker_code === selectedCode) ?? null
          setTrackerDetail(fallback)
          setLoadingDetail(false)
        }
      })
    return () => { cancelled = true }
  }, [selectedCode, refreshKey]) // eslint-disable-line react-hooks/exhaustive-deps

  const tracker = trackerDetail ?? trackers.find(t => t.tracker_code === selectedCode) ?? null
  const products = tracker?.tracked_products || []
  const effectiveAsinIdx = products.length === 0 ? 0 : Math.min(selectedAsinIdx, products.length - 1)
  const selectedProduct = products[effectiveAsinIdx]

  // Load product detail and timeline when ASIN selection changes
  useEffect(() => {
    if (!selectedProduct || !tracker) return
    let cancelled = false
    const load = async () => {
      const detail = await apiGetProductDetail(tracker.marketplace, selectedProduct.asin).catch(() => null)
      if (!cancelled) setProductDetail(detail)

      // Timeline may 500 due to backend bug — handle gracefully
      const tl = await apiGetProductTimeline(tracker.marketplace, selectedProduct.asin, {
        granularity: chartTimeframe,
        tracker_code: tracker.tracker_code,
      }).catch(() => null)
      if (!cancelled) setTimeline(tl)

      // Load events independently so they show even when timeline fails
      const evRes = await apiListEvents({
        marketplace: tracker.marketplace,
        asin: selectedProduct.asin,
        tracker_type: "COMPETITOR",
        tracker_code: tracker.tracker_code,
        page_size: 50,
      }).catch(() => null)
      if (!cancelled) setEvents(evRes?.items ?? [])
    }
    load()
    return () => { cancelled = true }
  }, [selectedProduct, tracker, chartTimeframe])

  if (trackers.length === 0) return (
    <>
      {showCreate && <CreateTrackerModal onClose={() => setShowCreate(false)} onCreate={t => { setTrackers([t]); setSelectedCode(t.tracker_code); setShowCreate(false) }} />}
      <div className="anim-fade">
        <PageHeader title="Competitor Tracker" sub="Deep dive analysis of manually tracked ASINs"
          actions={<button className="btn-primary" onClick={() => setShowCreate(true)}><Plus size={14} /> New Tracker</button>} />
        <div style={{ textAlign: "center", padding: "80px 24px", color: T.text3 }}>
          {loading
            ? <div style={{ fontSize: 13 }}>Loading trackers…</div>
            : <>
              <Package size={40} style={{ margin: "0 auto 16px", opacity: 0.3 }} />
              <div style={{ fontSize: 15, fontWeight: 600, color: T.text1, marginBottom: 6 }}>No competitor trackers yet</div>
              <div style={{ fontSize: 12, color: error ? T.red : T.text3, marginBottom: 24 }}>
                {error ?? "Add ASINs you want to track for price, availability, and listing changes."}
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

  const dualAxisData = timeline?.points.map(pt => ({
    date: pt.snapshot_date,
    bsr: pt.bsr_position ?? null,
    price: pt.price_current ?? null,
  })) || []
  const chartCurrency = productDetail?.current_state.currency ?? selectedProduct?.currency ?? "USD"
  const chartCurrencySymbol = chartCurrency === "EUR" ? "EUR " : chartCurrency === "GBP" ? "GBP " : "$"
  const bsrDomain = paddedIntegerDomain(dualAxisData.map(pt => pt.bsr), { minSpan: 10, floor: 1 })
  const priceDomain = paddedDomain(dualAxisData.map(pt => pt.price), { minSpan: 1, floor: 0 })

  const ratingData = timeline?.points.map(pt => ({
    date: pt.snapshot_date,
    rating: pt.rating_value ?? null,
    reviews: pt.review_count ?? null,
    availability: pt.availability_status,
    coupon: pt.coupon_text,
    deal: pt.deal_info,
  })) || []
  const ratingDomain = paddedDomain(ratingData.map(pt => pt.rating), { paddingRatio: 0.2, minSpan: 0.4, floor: 0, ceil: 5 })
  const reviewsDomain = paddedIntegerDomain(ratingData.map(pt => pt.reviews), { minSpan: 20, floor: 0 })

  return (
    <>
      {showCreate && (
        <CreateTrackerModal
          onClose={() => setShowCreate(false)}
          onCreate={t => { setTrackers(prev => [t, ...prev]); setSelectedCode(t.tracker_code); setShowCreate(false) }}
        />
      )}
      {showEdit && tracker && (
        <EditTrackerModal
          tracker={tracker}
          onClose={() => setShowEdit(false)}
          onUpdate={updated => {
            setTrackers(prev => prev.map(t => t.tracker_code === updated.tracker_code ? updated : t))
            setTrackerDetail(updated)
            setShowEdit(false)
          }}
          onDelete={code => {
            setTrackers(prev => prev.filter(t => t.tracker_code !== code))
            setSelectedCode("")
            setTrackerDetail(null)
            setShowEdit(false)
          }}
        />
      )}
        {showManageAsins && tracker && (
          <ManageAsinsModal
            tracker={tracker}
            onClose={() => setShowManageAsins(false)}
            onUpdate={updated => {
              setTrackers(prev => prev.map(t => t.tracker_code === updated.tracker_code ? updated : t))
              setTrackerDetail(updated)
              setSelectedAsinIdx(0)
              setProductDetail(null)
              setTimeline(null)
              setEvents([])
              setShowManageAsins(false)
            }}
          />
        )}
      <div className="anim-fade">
        <PageHeader title="Competitor Tracker" sub="Deep dive analysis of manually tracked ASINs"
          actions={
            <div style={{ display: "flex", gap: 8 }}>
              {tracker && (
                <>
                  <button className="btn-ghost" onClick={() => setShowEdit(true)}
                    style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
                    <Edit2 size={14} /> Edit Tracker
                  </button>
                  <button className="btn-ghost" onClick={() => setShowManageAsins(true)}
                    style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
                    <Settings size={14} /> Manage ASINs
                  </button>
                </>
              )}
              <button className="btn-primary" onClick={() => setShowCreate(true)}><Plus size={14} /> New Tracker</button>
            </div>
          } />

        {/* Status filter tabs */}
        <StatusFilterTabs trackers={trackers} value={statusFilter} onChange={setStatusFilter} />

        {/* Tracker selector */}
        <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
          {trackers.filter(t => (t.status ?? "ACTIVE") === statusFilter).map(t => {
            const isSelected = t.tracker_code === selectedCode
            return (
              <button key={t.tracker_code} onClick={() => {
                setTrackerDetail(null)
                setSelectedAsinIdx(0)
                setProductDetail(null)
                setTimeline(null)
                setEvents([])
                setLoadingDetail(true)
                setSelectedCode(t.tracker_code)
                setRefreshKey(k => k + 1)
                setTablePage(0)
                setEventsPage(0)
                setOpenCouponRowKey(null)
                setOpenDealRowKey(null)
              }}
                style={{ padding: "7px 14px", borderRadius: 8, border: `1px solid ${isSelected ? statusColor(t.status) : T.border}`, background: isSelected ? T.bg4 : T.bg2, color: isSelected ? statusColor(t.status) : T.text1, fontSize: 13, fontFamily: T.sans, cursor: "pointer", transition: "all .15s", display: "flex", alignItems: "center", gap: 6 }}>
                {isSelected && <span className="dot-live" style={{ background: statusColor(t.status), boxShadow: `0 0 0 3px ${statusColor(t.status)}30` }} />}
                {t.name}
                <span style={{ fontSize: 10, fontFamily: T.mono, color: T.text3 }}>({t.marketplace})</span>
              </button>
            )
          })}
        </div>

        {/* Tracker Info Header */}
        {tracker && (
          <TrackerInfoCard
            name={tracker.name}
            marketplace={tracker.marketplace}
            status={tracker.status}
            meta={`${tracker.stats.tracked_asin_count} ASINs · ${tracker.schedule.frequency} @ ${tracker.schedule.hour_utc}:00 UTC`}
            statsRight={
              <>
                {tracker.stats.last_success_at && (
                  <TrackerStat label="Last capture" value={new Date(tracker.stats.last_success_at).toLocaleDateString()} />
                )}
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap", justifyContent: "flex-end" }}>
                  {Object.entries(tracker.track_fields).filter(([, v]) => v).map(([k]) => (
                    <span key={k} style={{ fontSize: 9, padding: "2px 6px", background: T.bg4, border: `1px solid ${T.border}`, borderRadius: 4, color: T.text2, fontFamily: T.mono }}>
                      {k.replace(/_/g, " ")}
                    </span>
                  ))}
                </div>
              </>
            }
          />
        )}

        <div style={{ display: "grid", gridTemplateColumns: "240px 1fr", gap: 16 }}>
          {/* ASIN list */}
          <div>
            <div style={{ fontSize: 10, fontWeight: 600, color: T.text3, letterSpacing: ".08em", textTransform: "uppercase", marginBottom: 8, padding: "0 4px" }}>
              {loadingDetail ? "Loading…" : `${products.length} ASINs tracked`}
            </div>
            {products.map((p: TrackedProductSummary, i: number) => (
              <div key={i} className="row-hover" onClick={() => { setSelectedAsinIdx(i); setTablePage(0); setEventsPage(0); setOpenCouponRowKey(null); setOpenDealRowKey(null) }}
                style={{ padding: "10px 12px", borderRadius: 8, marginBottom: 4, background: i === selectedAsinIdx ? T.bg4 : T.bg2, border: `1px solid ${i === selectedAsinIdx ? T.border2 : T.border}`, cursor: "pointer", transition: "all .15s" }}>
                <div style={{ fontSize: 11, fontFamily: T.mono, color: T.text3, marginBottom: 3 }}>{p.asin}</div>
                <div style={{ fontSize: 12, color: T.text0, fontWeight: 500, lineHeight: 1.3, marginBottom: 6, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{p.title}</div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr auto", alignItems: "center", gap: 6 }}>
                  <span style={{ fontFamily: T.mono, fontSize: 12, color: T.amber }}>
                    {p.current_bsr_position ? `#${p.current_bsr_position.toLocaleString()}` : "—"}
                  </span>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, justifyContent: "flex-end" }}>
                    {p.recent_event_count_7d && p.recent_event_count_7d > 0 && (
                      <span style={{ fontSize: 9, padding: "1px 5px", background: `${T.amber}20`, color: T.amber, borderRadius: 4, fontFamily: T.mono, fontWeight: 700, minWidth: 42, textAlign: "center" }}>
                        {p.recent_event_count_7d} events
                      </span>
                    )}
                    {p.availability_status === "OUT_OF_STOCK"
                      ? <Badge type="stock" text="OOS" />
                      : <span className="dot-live" style={{ display: "inline-block", width: 6, height: 6 }} />}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Detail panel */}
          <div key={selectedProduct?.asin} className="anim-slide">
            {/* Top info from ProductDetail */}
            <div className="card" style={{ marginBottom: 12 }}>
              <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
                <ThumbnailImage
                  src={productDetail?.main_image_url_latest}
                  alt={productDetail?.title_latest || "Product image"}
                  size={52}
                  fallback="IMG"
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 15, fontWeight: 600, color: T.text0, marginBottom: 3 }}>
                    {productDetail?.title_latest || selectedProduct?.title || "—"}
                  </div>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 6 }}>
                    {(() => {
                      const url = productDetail?.product_url || selectedProduct?.product_url
                      return url
                        ? <a href={url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 11, fontFamily: T.mono, color: T.blue, textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 3 }}>{selectedProduct?.asin}<ExternalLink size={9} /></a>
                        : <span style={{ fontSize: 11, fontFamily: T.mono, color: T.text3 }}>{selectedProduct?.asin}</span>
                    })()}
                    <span style={{ fontSize: 11, color: T.text2 }}>{productDetail?.brand || selectedProduct?.brand}</span>
                    <Badge type={selectedProduct?.availability_status === "IN_STOCK" ? "listing" : "stock"} text={selectedProduct?.availability_status === "IN_STOCK" ? "In Stock" : "Out of Stock"} />
                  </div>
                  {/* Product state */}
                  {productDetail?.current_state && (
                    <div style={{ display: "flex", gap: 12, fontSize: 11, color: T.text1, flexWrap: "wrap" }}>
                      {productDetail.current_state.coupon_text && (
                        <span style={{ padding: "2px 8px", background: T.bg4, borderRadius: 4, color: T.amber }}>
                          🏷️ {productDetail.current_state.coupon_text}
                        </span>
                      )}
                      {productDetail.current_state.deal_info && (
                        <span style={{ padding: "2px 8px", background: `${T.blue}18`, borderRadius: 4, color: T.blue }}>
                          🎯 Deal Active
                        </span>
                      )}
                    </div>
                  )}
                  {/* Tracker refs */}
                  {productDetail?.tracker_refs && productDetail.tracker_refs.length > 0 && (
                    <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
                      {productDetail.tracker_refs.map(tr => (
                        <span key={tr.tracker_code} style={{ fontSize: 9, padding: "2px 6px", background: T.bg4, border: `1px solid ${T.border}`, borderRadius: 4, color: T.text2, fontFamily: T.mono }}>
                          {tr.tracker_type === "CATEGORY" ? "📊" : "🎯"} {tr.tracker_name}
                        </span>
                      ))}
                    </div>
                  )}
                  {/* First/Last seen */}
                  {(productDetail?.first_seen_at || productDetail?.last_seen_at) && (
                    <div style={{ display: "flex", gap: 12, marginTop: 6, fontSize: 10, color: T.text3, fontFamily: T.mono }}>
                      {productDetail.first_seen_at && <span>First seen: {new Date(productDetail.first_seen_at).toLocaleDateString()}</span>}
                      {productDetail.last_seen_at && <span>Last seen: {new Date(productDetail.last_seen_at).toLocaleDateString()}</span>}
                    </div>
                  )}
                </div>
                <div style={{ display: "flex", gap: 20, flexShrink: 0 }}>
                  {(() => {
                    const currency = productDetail?.current_state.currency ?? selectedProduct?.currency ?? "USD"
                    const sym = currency === "EUR" ? "€" : currency === "GBP" ? "£" : "$"
                    const latestPt = timeline?.points[timeline.points.length - 1]
                    return [
                      { label: "BSR", v: latestPt?.bsr_position ? `#${latestPt.bsr_position.toLocaleString()}` : (productDetail?.current_state.bsr_position ? `#${productDetail.current_state.bsr_position.toLocaleString()}` : (selectedProduct?.current_bsr_position ? `#${selectedProduct.current_bsr_position.toLocaleString()}` : "—")), color: T.amber },
                      { label: "Price", v: `${sym}${(latestPt?.price_current ?? productDetail?.current_state.price_current ?? selectedProduct?.current_price ?? 0).toFixed(2)}`, color: T.text0 },
                  { label: "Rating", v: latestPt?.rating_value ? `${latestPt.rating_value}★` : (productDetail?.current_state.rating_value ? `${productDetail.current_state.rating_value}★` : "—"), color: T.green },
                  { label: "Reviews", v: latestPt?.review_count ? latestPt.review_count.toLocaleString() : (productDetail?.current_state.review_count ? productDetail.current_state.review_count.toLocaleString() : "—"), color: T.text2 },
                    ].map(s => (
                      <div key={s.label} style={{ textAlign: "center" }}>
                        <div style={{ fontSize: 16, fontWeight: 700, fontFamily: T.mono, color: s.color }}>{s.v}</div>
                        <div style={{ fontSize: 10, color: T.text3, marginTop: 2 }}>{s.label}</div>
                      </div>
                    ))
                  })()}
                </div>
              </div>
            </div>

            {/* BSR vs Price Chart from Timeline */}
            <div className="card" style={{ marginBottom: 12 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
                <div>
                  <span style={{ fontSize: 13, fontWeight: 600, color: T.text1 }}>BSR vs Price Trend</span>
                  {timeline && (
                    <span style={{ fontSize: 11, color: T.text3, marginLeft: 8 }}>
                      {timeline.from_date} to {timeline.to_date}
                    </span>
                  )}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  {/* Timeframe toggle — US 3.3 */}
                  <div style={{ display: "flex", gap: 3 }}>
                    {(["DAILY", "WEEKLY", "MONTHLY"] as Timeframe[]).map(t => (
                      <button key={t} onClick={() => setChartTimeframe(t)}
                        style={{ padding: "4px 8px", borderRadius: 5, border: `1px solid ${t === chartTimeframe ? T.amber : T.border}`, background: t === chartTimeframe ? T.bg4 : "transparent", color: t === chartTimeframe ? T.amber : T.text3, fontSize: 10, fontWeight: 600, cursor: "pointer", textTransform: "capitalize" }}>
                        {t.toLowerCase()}
                      </button>
                    ))}
                  </div>
                  {timeline?.summary && (
                    <div style={{ display: "flex", gap: 8, fontSize: 10, fontFamily: T.mono }}>
                      <span style={{ color: T.blue }}>💰 {timeline.summary.price_change_count} price</span>
                      <span style={{ color: T.teal }}>📝 {timeline.summary.listing_change_count} listing</span>
                      <span style={{ color: T.purple }}>📦 {timeline.summary.availability_change_count} stock</span>
                    </div>
                  )}
                </div>
              </div>
              {dualAxisData.length > 0 ? (
                <ResponsiveContainer width="100%" height={250}>
                  <ComposedChart data={dualAxisData} margin={{ top: 12, right: 54, left: 8, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={T.border} vertical={false} />
                    <XAxis dataKey="date" minTickGap={28} tick={{ fill: T.text3, fontSize: 9, fontFamily: T.mono }} axisLine={false} tickLine={false} />
                    <YAxis yAxisId="left" reversed domain={bsrDomain} width={48} tickCount={4} allowDecimals={false} tick={{ fill: T.text3, fontSize: 9, fontFamily: T.mono }} axisLine={false} tickLine={false} tickFormatter={(v: number) => `#${formatCompactNumber(v)}`} />
                    <YAxis yAxisId="right" orientation="right" domain={priceDomain} width={58} tickCount={4} tick={{ fill: T.text3, fontSize: 9, fontFamily: T.mono }} axisLine={false} tickLine={false} tickFormatter={(v: number) => formatMoneyAxisTick(v, chartCurrencySymbol, priceDomain)} />
                    <Tooltip formatter={(value, name) => name === "Price" ? [`${chartCurrencySymbol}${Number(value ?? 0).toFixed(2)}`, name] : [`#${Number(value ?? 0).toLocaleString()}`, name]} contentStyle={{ background: T.bg4, border: `1px solid ${T.border}`, borderRadius: 8, fontFamily: T.mono, fontSize: 11 }} />
                    <Legend wrapperStyle={{ color: T.text1, fontSize: 11 }} />
                    <Line yAxisId="left" type="monotone" dataKey="bsr" stroke={T.amber} strokeWidth={2.25} name="BSR Rank" dot={dualAxisData.length <= 12 ? { r: 2, fill: T.amber } : false} activeDot={{ r: 4 }} connectNulls={false} strokeLinecap="round" strokeLinejoin="round" />
                    <Line yAxisId="right" type="monotone" dataKey="price" stroke={T.green} strokeWidth={2.25} strokeDasharray="4 4" name="Price" dot={dualAxisData.length <= 12 ? { r: 2, fill: T.green } : false} activeDot={{ r: 4 }} connectNulls={false} strokeLinecap="round" strokeLinejoin="round" />
                  </ComposedChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ textAlign: "center", padding: "40px 0", color: T.text3, fontSize: 12 }}>
                  <AlertCircle size={20} style={{ marginBottom: 6, opacity: 0.5 }} /><br />
                  Timeline data unavailable — chart cannot be rendered.<br />
                  <span style={{ fontSize: 11, opacity: 0.7 }}>The server returned an error for the timeline endpoint.</span>
                </div>
              )}
            </div>

            {/* Rating & Reviews Chart */}
            <div className="card" style={{ marginBottom: 12 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
                <div>
                  <span style={{ fontSize: 13, fontWeight: 600, color: T.text1 }}>Rating &amp; Reviews Trend</span>
                  {timeline && (
                    <span style={{ fontSize: 11, color: T.text3, marginLeft: 8 }}>
                      {timeline.from_date} to {timeline.to_date}
                    </span>
                  )}
                </div>
              </div>
              {ratingData.length > 0 ? (
                <>
                  <ResponsiveContainer width="100%" height={220}>
                    <ComposedChart data={ratingData} margin={{ top: 12, right: 54, left: 8, bottom: 4 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke={T.border} vertical={false} />
                      <XAxis dataKey="date" minTickGap={28} tick={{ fill: T.text3, fontSize: 9, fontFamily: T.mono }} axisLine={false} tickLine={false} />
                      <YAxis yAxisId="left" domain={ratingDomain} width={42} tickCount={4} tick={{ fill: T.text3, fontSize: 9, fontFamily: T.mono }} axisLine={false} tickLine={false} tickFormatter={(v: number) => `${Number(v).toFixed(1)}`} />
                      <YAxis yAxisId="right" orientation="right" domain={reviewsDomain} width={48} tickCount={4} allowDecimals={false} tick={{ fill: T.text3, fontSize: 9, fontFamily: T.mono }} axisLine={false} tickLine={false} tickFormatter={(v: number) => formatCompactNumber(v)} />
                      <Tooltip formatter={(value, name) => name === "Rating" ? [`${Number(value ?? 0).toFixed(1)}/5`, name] : [Number(value ?? 0).toLocaleString(), name]} contentStyle={{ background: T.bg4, border: `1px solid ${T.border}`, borderRadius: 8, fontFamily: T.mono, fontSize: 11 }} />
                      <Legend wrapperStyle={{ color: T.text1, fontSize: 11 }} />
                      <Line yAxisId="left" type="monotone" dataKey="rating" stroke={T.green} strokeWidth={2.25} name="Rating" dot={ratingData.length <= 12 ? { r: 2, fill: T.green } : false} activeDot={{ r: 4 }} connectNulls={false} strokeLinecap="round" strokeLinejoin="round" />
                      <Line yAxisId="right" type="monotone" dataKey="reviews" stroke={T.blue} strokeWidth={2.25} strokeDasharray="4 4" name="Reviews" dot={ratingData.length <= 12 ? { r: 2, fill: T.blue } : false} activeDot={{ r: 4 }} connectNulls={false} strokeLinecap="round" strokeLinejoin="round" />
                    </ComposedChart>
                  </ResponsiveContainer>

                  {/* Per-day status strip */}
                  <div style={{ overflowX: "auto", marginTop: 14 }}>
                    <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 500 }}>
                      <thead>
                        <tr>
                          {["Date", "Availability", "Deal", "Coupon"].map(h => (
                            <th key={h} className="th-border">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {ratingData.slice(tablePage * 7, (tablePage + 1) * 7).map(r => (
                          <tr key={r.date} style={{ borderBottom: `1px solid ${T.border}` }}>
                            <td style={{ padding: "6px 10px", fontFamily: T.mono, fontSize: 11, color: T.text2 }}>{r.date}</td>
                            <td style={{ padding: "6px 10px" }}>
                              <Badge type={r.availability === "IN_STOCK" ? "listing" : "stock"} text={r.availability === "IN_STOCK" ? "In Stock" : r.availability === "OUT_OF_STOCK" ? "OOS" : r.availability ?? "—"} />
                            </td>
                            <td style={{ padding: "6px 10px" }}>
                              {(() => {
                                const items = parseDealItems(r.deal)
                                if (items.length === 0) return <span style={{ color: T.text3 }}>—</span>
                                return (
                                  <ExpandableList
                                    items={items}
                                    label="Deal"
                                    isOpen={openDealRowKey === r.date}
                                    onToggle={() => setOpenDealRowKey(prev => prev === r.date ? null : r.date)}
                                    fontSize={9}
                                    padding="2px 6px"
                                    borderRadius={4}
                                    minWidth={180}
                                  />
                                )
                              })()}
                            </td>
                            <td style={{ padding: "6px 10px" }}>
                              {(() => {
                                const items = parseCouponItems(r.coupon)
                                if (items.length === 0) return <span style={{ color: T.text3 }}>—</span>
                                return (
                                  <ExpandableList
                                    items={items}
                                    label={`${items.length} Coupon${items.length > 1 ? "s" : ""}`}
                                    isOpen={openCouponRowKey === r.date}
                                    onToggle={() => setOpenCouponRowKey(prev => prev === r.date ? null : r.date)}
                                    color={T.amber}
                                    colorBorder={T.amberD}
                                    colorBg={`${T.amber}14`}
                                    fontSize={9}
                                    padding="2px 6px"
                                    borderRadius={4}
                                    minWidth={180}
                                  />
                                )
                              })()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {ratingData.length > 7 && (
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 8, padding: "4px 0" }}>
                        <span style={{ fontSize: 11, color: T.text3, fontFamily: T.mono }}>
                          {tablePage * 7 + 1}–{Math.min((tablePage + 1) * 7, ratingData.length)} of {ratingData.length}
                        </span>
                        <div style={{ display: "flex", gap: 6 }}>
                          <button onClick={() => setTablePage(p => Math.max(0, p - 1))} disabled={tablePage === 0}
                            style={{ padding: "3px 10px", borderRadius: 5, border: `1px solid ${T.border}`, background: "none", color: tablePage === 0 ? T.text3 : T.text1, cursor: tablePage === 0 ? "default" : "pointer", fontSize: 11, fontFamily: T.mono }}>
                            ‹ Prev
                          </button>
                          <button onClick={() => setTablePage(p => Math.min(Math.ceil(ratingData.length / 7) - 1, p + 1))} disabled={(tablePage + 1) * 7 >= ratingData.length}
                            style={{ padding: "3px 10px", borderRadius: 5, border: `1px solid ${T.border}`, background: "none", color: (tablePage + 1) * 7 >= ratingData.length ? T.text3 : T.text1, cursor: (tablePage + 1) * 7 >= ratingData.length ? "default" : "pointer", fontSize: 11, fontFamily: T.mono }}>
                            Next ›
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div style={{ textAlign: "center", padding: "40px 0", color: T.text3, fontSize: 12 }}>
                  <AlertCircle size={20} style={{ marginBottom: 6, opacity: 0.5 }} /><br />
                  Timeline data unavailable — chart cannot be rendered.
                </div>
              )}
            </div>

            {/* Events — uses standalone events state (works even when timeline 500s) */}
            <div className="card">
              <div style={{ fontSize: 13, fontWeight: 600, color: T.text1, marginBottom: 12 }}>Product Events</div>
              {events.length === 0 && (
                <div style={{ textAlign: "center", padding: "30px 0", color: T.text3, fontSize: 12 }}>No events recorded for this product</div>
              )}
              {events.slice(eventsPage * 10, (eventsPage + 1) * 10).map((ev) => {
                const meta = AlertTypeMeta(ev.event_type)
                return (
                  <div key={ev.event_code} style={{ display: "flex", gap: 10, padding: "8px 0", borderBottom: `1px solid ${T.border}` }}>
                    <span style={{ color: meta.color, marginTop: 1, flexShrink: 0 }}>{meta.icon}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
                        <Badge type={meta.badgeType} text={meta.label} />
                        <Badge type={ev.severity === "HIGH" ? "exit" : ev.severity === "MEDIUM" ? "top10" : "info"} text={ev.severity} />
                      </div>
                      <div style={{ fontSize: 12, color: T.text0 }}>{ev.title}</div>
                      <div style={{ fontSize: 11, color: T.text2, marginTop: 2 }}>{ev.summary}</div>
                      <div style={{ fontSize: 10, fontFamily: T.mono, color: T.text3, marginTop: 2 }}>
                        {new Date(ev.event_time).toLocaleString()} · {ev.snapshot_date}
                      </div>
                    </div>
                  </div>
                )
              })}
              {events.length > 10 && (
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 8, padding: "4px 0" }}>
                  <span style={{ fontSize: 11, color: T.text3, fontFamily: T.mono }}>
                    {eventsPage * 10 + 1}–{Math.min((eventsPage + 1) * 10, events.length)} of {events.length}
                  </span>
                  <div style={{ display: "flex", gap: 6 }}>
                    <button onClick={() => setEventsPage(p => Math.max(0, p - 1))} disabled={eventsPage === 0}
                      style={{ padding: "3px 10px", borderRadius: 5, border: `1px solid ${T.border}`, background: "none", color: eventsPage === 0 ? T.text3 : T.text1, cursor: eventsPage === 0 ? "default" : "pointer", fontSize: 11, fontFamily: T.mono }}>
                      ‹ Prev
                    </button>
                    <button onClick={() => setEventsPage(p => Math.min(Math.ceil(events.length / 10) - 1, p + 1))} disabled={(eventsPage + 1) * 10 >= events.length}
                      style={{ padding: "3px 10px", borderRadius: 5, border: `1px solid ${T.border}`, background: "none", color: (eventsPage + 1) * 10 >= events.length ? T.text3 : T.text1, cursor: (eventsPage + 1) * 10 >= events.length ? "default" : "pointer", fontSize: 11, fontFamily: T.mono }}>
                      Next ›
                    </button>
                  </div>
                </div>
              )}
              {/* Link to Amazon */}
              {selectedProduct && (
                <a href={selectedProduct.product_url || ""} target="_blank" rel="noopener noreferrer"
                  style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6, marginTop: 12, padding: "8px 0", color: T.blue, fontSize: 12, textDecoration: "none" }}>
                  <ExternalLink size={13} /> View on Amazon
                </a>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
