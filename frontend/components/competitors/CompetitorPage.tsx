"use client"

import { useState, useEffect } from "react"
import { ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts"
import { Plus, ExternalLink, Calendar, Settings, Clock, X, Trash2, CheckCircle, AlertCircle, Edit2 } from "lucide-react"
import { T } from "../shared/DesignTokens"
import { PageHeader } from "../shared/PageHeader"
import { Badge } from "../shared/Badge"
import { AlertTypeMeta } from "../shared/AlertTypeMeta"
import { apiListCompetitorTrackers, apiGetCompetitorTracker, apiGetProductDetail, apiGetProductTimeline, apiCreateCompetitorTracker, apiUpdateCompetitorTracker, apiReplaceTrackedAsins, apiListEvents } from "../shared/api"
import type { CompetitorTrackerDetail, TrackedProductSummary, ProductDetail, ProductTimelineResponse, CompetitorTrackerCreateRequest, CompetitorTrackerUpdateRequest, CompetitorTrackFields, Timeframe, Event, TrackerStatus } from "../shared/types"

const MARKETPLACES = [
  "amazon_us", "amazon_de", "amazon_uk", "amazon_fr",
  "amazon_it", "amazon_es", "amazon_ca", "amazon_jp",
]

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
  const [asins, setAsins] = useState<string[]>(tracker.tracked_asins.map(a => a.asin))
  const [asinInput, setAsinInput] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const addAsin = () => {
    const raw = asinInput.trim().toUpperCase()
    if (!raw) return
    if (!/^[A-Z0-9]{10}$/.test(raw)) { setError("Invalid ASIN — must be 10 alphanumeric characters."); return }
    if (asins.includes(raw)) { setError("ASIN already in list."); return }
    if (asins.length >= 200) { setError("Maximum 200 ASINs per tracker."); return }
    setAsins(prev => [...prev, raw])
    setAsinInput("")
    setError(null)
  }

  const removeAsin = (asin: string) => setAsins(prev => prev.filter(a => a !== asin))

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (asins.length === 0) { setError("At least one ASIN is required."); return }
    setSubmitting(true)
    try {
      const updated = await apiReplaceTrackedAsins(
        tracker.tracker_code,
        asins.map(asin => ({ asin, enabled: true }))
      )
      onUpdate(updated)
    } catch {
      setError("Failed to update ASINs. Please try again.")
      setSubmitting(false)
    }
  }

  const inputStyle: React.CSSProperties = {
    width: "100%", padding: "9px 12px", borderRadius: 8,
    border: `1px solid ${T.border}`, background: T.bg3,
    color: T.text0, fontSize: 13, fontFamily: T.sans, outline: "none",
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
            <label style={{ display: "block", fontSize: 11, fontWeight: 600, color: T.text2, marginBottom: 5, letterSpacing: ".04em", textTransform: "uppercase" }}>ASINs ({asins.length}/200)</label>
            <div style={{ display: "flex", gap: 8 }}>
              <input
                type="text" value={asinInput}
                onChange={e => { setAsinInput(e.target.value.toUpperCase()); setError(null) }}
                onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); addAsin() } }}
                placeholder="B0ABC12345"
                maxLength={10}
                style={{ ...inputStyle, fontFamily: T.mono, flex: 1 }}
              />
              <button type="button" onClick={addAsin}
                style={{ padding: "9px 14px", borderRadius: 8, border: `1px solid ${T.border}`, background: T.bg4, color: T.text0, cursor: "pointer", fontSize: 13, fontFamily: T.sans, flexShrink: 0, display: "flex", alignItems: "center", gap: 6 }}>
                <Plus size={13} /> Add
              </button>
            </div>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 16, maxHeight: 200, overflowY: "auto" }}>
            {asins.map(asin => (
              <span key={asin} style={{ display: "inline-flex", alignItems: "center", gap: 5, padding: "3px 8px", background: T.bg4, border: `1px solid ${T.border2}`, borderRadius: 6, fontSize: 11, fontFamily: T.mono, color: T.amber }}>
                {asin}
                <button type="button" onClick={() => removeAsin(asin)} style={{ background: "none", border: "none", color: T.text3, cursor: "pointer", padding: 0, display: "flex", lineHeight: 1 }}><Trash2 size={10} /></button>
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
}: {
  tracker: CompetitorTrackerDetail
  onClose: () => void
  onUpdate: (updated: CompetitorTrackerDetail) => void
}) => {
  const [name, setName] = useState(tracker.name)
  const [trackFields, setTrackFields] = useState<CompetitorTrackFields>({ ...tracker.track_fields })
  const [hourUtc, setHourUtc] = useState(tracker.schedule.hour_utc)
  const [status, setStatus] = useState<TrackerStatus>(tracker.status)
  const [submitting, setSubmitting] = useState(false)
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

  const inputStyle: React.CSSProperties = {
    width: "100%", padding: "9px 12px", borderRadius: 8,
    border: `1px solid ${T.border}`, background: T.bg3,
    color: T.text0, fontSize: 13, fontFamily: T.sans, outline: "none",
  }
  const labelStyle: React.CSSProperties = {
    display: "block", fontSize: 11, fontWeight: 600, color: T.text2,
    marginBottom: 5, letterSpacing: ".04em", textTransform: "uppercase",
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
            <label style={labelStyle}>Tracker Name</label>
            <input type="text" value={name} onChange={e => setName(e.target.value)} maxLength={120} style={inputStyle} />
          </div>

          {/* Track fields */}
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>Track Fields</label>
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
            <label style={labelStyle}>Run at (UTC hour)</label>
            <select value={hourUtc} onChange={e => setHourUtc(Number(e.target.value))} style={{ ...inputStyle, cursor: "pointer" }}>
              {Array.from({ length: 24 }, (_, i) => (
                <option key={i} value={i}>{String(i).padStart(2, "0")}:00 UTC</option>
              ))}
            </select>
          </div>

          {/* Status */}
          <div style={{ marginBottom: 20 }}>
            <label style={labelStyle}>Status</label>
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
    } catch {
      setError("Failed to create tracker. Please try again.")
      setSubmitting(false)
    }
  }

  const inputStyle: React.CSSProperties = {
    width: "100%", padding: "9px 12px", borderRadius: 8,
    border: `1px solid ${T.border}`, background: T.bg3,
    color: T.text0, fontSize: 13, fontFamily: T.sans, outline: "none",
  }
  const labelStyle: React.CSSProperties = {
    display: "block", fontSize: 11, fontWeight: 600, color: T.text2,
    marginBottom: 5, letterSpacing: ".04em", textTransform: "uppercase",
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
            <label style={labelStyle}>Tracker Name</label>
            <input type="text" value={name} onChange={e => setName(e.target.value)} maxLength={120} placeholder="e.g. Bottle Warmer Competitors - US" style={inputStyle} />
          </div>

          {/* Marketplace */}
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>Marketplace</label>
            <select value={marketplace} onChange={e => setMarketplace(e.target.value)} style={{ ...inputStyle, cursor: "pointer" }}>
              {MARKETPLACES.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>

          {/* ASIN input */}
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>ASINs ({asins.length}/200)</label>
            <div style={{ display: "flex", gap: 8 }}>
              <input
                type="text" value={asinInput}
                onChange={e => { setAsinInput(e.target.value.toUpperCase()); setError(null) }}
                onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); addAsin() } }}
                placeholder="B0ABC12345"
                maxLength={10}
                style={{ ...inputStyle, fontFamily: T.mono, flex: 1 }}
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
            <label style={labelStyle}>Track Fields</label>
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
            <label style={labelStyle}>Run at (UTC hour)</label>
            <select value={hourUtc} onChange={e => setHourUtc(Number(e.target.value))} style={{ ...inputStyle, cursor: "pointer" }}>
              {Array.from({ length: 24 }, (_, i) => (
                <option key={i} value={i}>{String(i).padStart(2, "0")}:00 UTC</option>
              ))}
            </select>
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
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [showEdit, setShowEdit] = useState(false)
  const [showManageAsins, setShowManageAsins] = useState(false)
  const [chartTimeframe, setChartTimeframe] = useState<Timeframe>("DAILY")

  // Load tracker list only
  useEffect(() => {
    apiListCompetitorTrackers().then(res => {
      setTrackers(res.items as CompetitorTrackerDetail[])
      if (res.items.length > 0) setSelectedCode(res.items[0].tracker_code)
      setLoading(false)
    })
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
  }, [selectedCode]) // eslint-disable-line react-hooks/exhaustive-deps

  const tracker = trackerDetail ?? trackers.find(t => t.tracker_code === selectedCode) ?? null
  const products = tracker?.tracked_products || []
  const selectedProduct = products[selectedAsinIdx]

  // Load product detail and timeline when ASIN selection changes
  useEffect(() => {
    if (!selectedProduct || !tracker) return
    let cancelled = false
    const load = async () => {
      const detail = await apiGetProductDetail(tracker.marketplace, selectedProduct.asin).catch(() => null)
      if (!cancelled) setProductDetail(detail)

      // Timeline may 500 due to backend bug — handle gracefully
      const tl = await apiGetProductTimeline(tracker.marketplace, selectedProduct.asin, { granularity: chartTimeframe }).catch(() => null)
      if (!cancelled) setTimeline(tl)

      // Load events independently so they show even when timeline fails
      const evRes = await apiListEvents({ marketplace: tracker.marketplace, asin: selectedProduct.asin, page_size: 50 }).catch(() => null)
      if (!cancelled) setEvents(evRes?.items ?? [])
    }
    load()
    return () => { cancelled = true }
  }, [selectedProduct, tracker, chartTimeframe])

  if (loading) return <div style={{ textAlign: "center", padding: 60, color: T.text3 }}>Loading competitor trackers...</div>
  if (trackers.length === 0) return (
    <>
      {showCreate && <CreateTrackerModal onClose={() => setShowCreate(false)} onCreate={t => { setTrackers([t]); setSelectedCode(t.tracker_code); setShowCreate(false) }} />}
      <div className="anim-fade">
        <PageHeader title="Competitor Tracker" sub="Deep dive analysis of manually tracked ASINs"
          actions={<button className="btn-primary" onClick={() => setShowCreate(true)}><Plus size={14} /> New Tracker</button>} />
        <div style={{ textAlign: "center", padding: 60, color: T.text3 }}>
          No competitor trackers configured.{" "}
          <button onClick={() => setShowCreate(true)} style={{ background: "none", border: "none", color: T.blue, cursor: "pointer", fontSize: 13 }}>Create one &rarr;</button>
        </div>
      </div>
    </>
  )

  const dualAxisData = timeline?.points.map(pt => ({
    date: pt.snapshot_date,
    bsr: pt.bsr_position,
    price: pt.price_current,
  })) || []

  const ratingData = timeline?.points.map(pt => ({
    date: pt.snapshot_date,
    rating: pt.rating_value,
    reviews: pt.review_count,
    availability: pt.availability_status,
    buyBox: pt.buy_box_status,
    coupon: pt.coupon_text,
    variations: pt.variation_count,
  })) || []

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
        />
      )}
      {showManageAsins && tracker && (
        <ManageAsinsModal
          tracker={tracker}
          onClose={() => setShowManageAsins(false)}
          onUpdate={updated => {
            setTrackers(prev => prev.map(t => t.tracker_code === updated.tracker_code ? updated : t))
            setTrackerDetail(updated)
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

      {/* Tracker selector tabs */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        {trackers.map(t => (
          <button key={t.tracker_code} onClick={() => {
              setTrackerDetail(null)
              setSelectedAsinIdx(0)
              setProductDetail(null)
              setTimeline(null)
              setEvents([])
              setLoadingDetail(true)
              setSelectedCode(t.tracker_code)
            }}
            style={{ padding: "7px 14px", borderRadius: 8, border: `1px solid ${t.tracker_code === selectedCode ? T.amber : T.border}`, background: t.tracker_code === selectedCode ? T.bg4 : T.bg2, color: t.tracker_code === selectedCode ? T.amber : T.text1, fontSize: 13, fontFamily: T.sans, cursor: "pointer", transition: "all .15s", display: "flex", alignItems: "center", gap: 6 }}>
            {t.tracker_code === selectedCode && <span className="dot-live" />}
            {t.name}
            <span style={{ fontSize: 10, fontFamily: T.mono, color: T.text3 }}>({t.marketplace})</span>
          </button>
        ))}
      </div>

      {/* Tracker Info Header */}
      {tracker && (
      <div className="card" style={{ marginBottom: 16, padding: "12px 16px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
              <span style={{ fontSize: 14, fontWeight: 700, color: T.text0 }}>{tracker.name}</span>
              <Badge type="top10" text={tracker.marketplace.toUpperCase()} />
              {tracker.status === "ACTIVE" && <span className="dot-live" />}
            </div>
            <div style={{ display: "flex", gap: 12, fontSize: 11, color: T.text3, fontFamily: T.mono }}>
              <span><Calendar size={10} /> {tracker.schedule.frequency} @ {tracker.schedule.hour_utc}:00 UTC</span>
              <span><Settings size={10} /> {tracker.stats.tracked_asin_count} ASINs</span>
              <span><Clock size={10} /> Last: {tracker.stats.last_success_at ? new Date(tracker.stats.last_success_at).toLocaleString() : "—"}</span>
            </div>
          </div>
          {/* Track fields */}
          <div style={{ display: "flex", gap: 4, flexWrap: "wrap", justifyContent: "flex-end" }}>
            {Object.entries(tracker.track_fields).filter(([, v]) => v).map(([k]) => (
              <span key={k} style={{ fontSize: 9, padding: "2px 6px", background: T.bg4, border: `1px solid ${T.border}`, borderRadius: 4, color: T.text2, fontFamily: T.mono }}>
                {k.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        </div>
      </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "240px 1fr", gap: 16 }}>
        {/* ASIN list */}
        <div>
          <div style={{ fontSize: 10, fontWeight: 600, color: T.text3, letterSpacing: ".08em", textTransform: "uppercase", marginBottom: 8, padding: "0 4px" }}>
            {loadingDetail ? "Loading…" : `${products.length} ASINs tracked`}
          </div>
          {products.map((p: TrackedProductSummary, i: number) => (
            <div key={p.asin} className="row-hover" onClick={() => setSelectedAsinIdx(i)}
              style={{ padding: "10px 12px", borderRadius: 8, marginBottom: 4, background: i === selectedAsinIdx ? T.bg4 : T.bg2, border: `1px solid ${i === selectedAsinIdx ? T.border2 : T.border}`, cursor: "pointer", transition: "all .15s" }}>
              <div style={{ fontSize: 11, fontFamily: T.mono, color: T.text3, marginBottom: 3 }}>{p.asin}</div>
              <div style={{ fontSize: 12, color: T.text0, fontWeight: 500, lineHeight: 1.3, marginBottom: 6, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{p.title}</div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span style={{ fontFamily: T.mono, fontSize: 12, color: T.amber }}>
                  {p.current_bsr_position ? `#${p.current_bsr_position.toLocaleString()}` : "—"}
                </span>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  {p.recent_event_count_7d && p.recent_event_count_7d > 0 && (
                    <span style={{ fontSize: 9, padding: "1px 5px", background: `${T.amber}20`, color: T.amber, borderRadius: 4, fontFamily: T.mono, fontWeight: 700 }}>
                      {p.recent_event_count_7d} events
                    </span>
                  )}
                  {p.availability_status === "OUT_OF_STOCK"
                    ? <Badge type="stock" text="OOS" />
                    : <span className="dot-live" />}
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
              <div style={{ width: 52, height: 52, borderRadius: 8, background: T.bg3, border: `1px solid ${T.border}`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, fontFamily: T.mono, color: T.text3, flexShrink: 0, overflow: "hidden" }}>
                {productDetail?.main_image_url_latest
                  // eslint-disable-next-line @next/next/no-img-element
                  ? <img src={productDetail.main_image_url_latest} alt={productDetail?.title_latest || "Product image"} style={{ width: "100%", height: "100%", objectFit: "cover" }} onError={e => { (e.target as HTMLImageElement).style.display = "none" }} />
                  : "IMG"}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 15, fontWeight: 600, color: T.text0, marginBottom: 3 }}>
                  {productDetail?.title_latest || selectedProduct?.title || "—"}
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 6 }}>
                  <span style={{ fontSize: 11, fontFamily: T.mono, color: T.text3 }}>{selectedProduct?.asin}</span>
                  <span style={{ fontSize: 11, color: T.text2 }}>{productDetail?.brand || selectedProduct?.brand}</span>
                  <Badge type={selectedProduct?.availability_status === "IN_STOCK" ? "listing" : "stock"} text={selectedProduct?.availability_status === "IN_STOCK" ? "In Stock" : "Out of Stock"} />
                </div>
                {/* Product state */}
                {productDetail?.current_state && (
                  <div style={{ display: "flex", gap: 12, fontSize: 11, color: T.text1, flexWrap: "wrap" }}>
                    <span><strong>Buy Box:</strong> {productDetail.current_state.buy_box_status === "HAS_BUY_BOX" ? `✅ ${productDetail.current_state.buy_box_seller_name || ""}` : "❌"}</span>
                    {productDetail.current_state.coupon_text && (
                      <span style={{ padding: "2px 8px", background: T.bg4, borderRadius: 4, color: T.amber }}>
                        🏷️ {productDetail.current_state.coupon_text}
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
                    { label: "BSR", v: productDetail?.current_state.bsr_position ? `#${productDetail.current_state.bsr_position.toLocaleString()}` : (selectedProduct?.current_bsr_position ? `#${selectedProduct.current_bsr_position.toLocaleString()}` : "—"), color: T.amber },
                    { label: "Price", v: `${sym}${(productDetail?.current_state.price_current ?? selectedProduct?.current_price ?? 0).toFixed(2)}`, color: T.text0 },
                    { label: "Rating", v: latestPt?.rating_value ? `${latestPt.rating_value}★` : "—", color: T.green },
                    { label: "Reviews", v: latestPt?.review_count ? latestPt.review_count.toLocaleString() : "—", color: T.text2 },
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
                <ComposedChart data={dualAxisData} margin={{ top: 20, right: 80, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={T.border} />
                  <XAxis dataKey="date" tick={{ fill: T.text3, fontSize: 9, fontFamily: T.mono }} axisLine={false} tickLine={false} />
                  <YAxis yAxisId="left" reversed tick={{ fill: T.text3, fontSize: 9, fontFamily: T.mono }} axisLine={false} tickLine={false} tickFormatter={v => `#${v}`} />
                  <YAxis yAxisId="right" orientation="right" tick={{ fill: T.text3, fontSize: 9, fontFamily: T.mono }} axisLine={false} tickLine={false} tickFormatter={v => `$${v}`} />
                  <Tooltip contentStyle={{ background: T.bg4, border: `1px solid ${T.border}`, borderRadius: 8, fontFamily: T.mono, fontSize: 11 }} />
                  <Legend wrapperStyle={{ color: T.text1, fontSize: 11 }} />
                  <Line yAxisId="left" type="monotone" dataKey="bsr" stroke={T.amber} strokeWidth={2.5} name="BSR Rank" dot={false} />
                  <Line yAxisId="right" type="monotone" dataKey="price" stroke={T.green} strokeWidth={2.5} strokeDasharray="5 5" name="Price ($)" dot={false} />
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
                  <ComposedChart data={ratingData} margin={{ top: 20, right: 80, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={T.border} />
                    <XAxis dataKey="date" tick={{ fill: T.text3, fontSize: 9, fontFamily: T.mono }} axisLine={false} tickLine={false} />
                    <YAxis yAxisId="left" domain={[0, 5]} tick={{ fill: T.text3, fontSize: 9, fontFamily: T.mono }} axisLine={false} tickLine={false} tickFormatter={(v: number) => `${v}★`} />
                    <YAxis yAxisId="right" orientation="right" tick={{ fill: T.text3, fontSize: 9, fontFamily: T.mono }} axisLine={false} tickLine={false} tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)} />
                    <Tooltip contentStyle={{ background: T.bg4, border: `1px solid ${T.border}`, borderRadius: 8, fontFamily: T.mono, fontSize: 11 }} />
                    <Legend wrapperStyle={{ color: T.text1, fontSize: 11 }} />
                    <Line yAxisId="left" type="monotone" dataKey="rating" stroke={T.green} strokeWidth={2.5} name="Rating ★" dot={{ r: 3, fill: T.green }} />
                    <Line yAxisId="right" type="monotone" dataKey="reviews" stroke={T.blue} strokeWidth={2.5} strokeDasharray="5 5" name="Reviews" dot={false} />
                  </ComposedChart>
                </ResponsiveContainer>

                {/* Per-day status strip */}
                <div style={{ overflowX: "auto", marginTop: 14 }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 500 }}>
                    <thead>
                      <tr>
                        {["Date", "Availability", "Buy Box", "Coupon", "Variants"].map(h => (
                          <th key={h} style={{ padding: "6px 10px", textAlign: "left", fontSize: 10, fontWeight: 600, color: T.text3, letterSpacing: ".06em", textTransform: "uppercase", fontFamily: T.mono, borderBottom: `1px solid ${T.border}` }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {ratingData.map(r => (
                        <tr key={r.date} style={{ borderBottom: `1px solid ${T.border}` }}>
                          <td style={{ padding: "6px 10px", fontFamily: T.mono, fontSize: 11, color: T.text2 }}>{r.date}</td>
                          <td style={{ padding: "6px 10px" }}>
                            <Badge type={r.availability === "IN_STOCK" ? "listing" : "stock"} text={r.availability === "IN_STOCK" ? "In Stock" : r.availability === "OUT_OF_STOCK" ? "OOS" : r.availability ?? "—"} />
                          </td>
                          <td style={{ padding: "6px 10px" }}>
                            <Badge type={r.buyBox === "HAS_BUY_BOX" ? "listing" : r.buyBox === "NO_BUY_BOX" ? "stock" : "info"} text={r.buyBox === "HAS_BUY_BOX" ? "Has BB" : r.buyBox === "NO_BUY_BOX" ? "No BB" : "—"} />
                          </td>
                          <td style={{ padding: "6px 10px", fontSize: 11, color: r.coupon ? T.amber : T.text3 }}>{r.coupon ?? "—"}</td>
                          <td style={{ padding: "6px 10px", fontFamily: T.mono, fontSize: 11, color: T.text2 }}>{r.variations != null ? r.variations : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
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
            {events.map((ev) => {
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
            {/* Link to Amazon */}
            {selectedProduct && (
              <a href={`https://www.amazon.com/dp/${selectedProduct.asin}`} target="_blank" rel="noopener noreferrer"
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
