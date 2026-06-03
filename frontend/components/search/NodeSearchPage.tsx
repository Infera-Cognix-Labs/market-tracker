"use client"

import { useState } from "react"
import { Search, ExternalLink, CheckCircle, AlertCircle, Plus } from "lucide-react"
import { T } from "../shared/DesignTokens"
import { PageHeader } from "../shared/PageHeader"
import { Badge } from "../shared/Badge"
import { apiCreateCategoryTracker, ApiError } from "../shared/api"
import type { CategoryTracker, CategoryTrackerCreateRequest } from "../shared/types"

// ── Parse browse node ID from an Amazon best-sellers URL ─────────────────────
function parseNodeId(input: string): string | null {
  const trimmed = input.trim()
  // Already a pure numeric ID
  if (/^\d+$/.test(trimmed)) return trimmed
  // Extract from URL: .../zgbs/<cat>/<nodeId> or node=<nodeId>
  const pathMatch = trimmed.match(/\/zgbs\/[^/]+\/(\d+)/)
  if (pathMatch) return pathMatch[1]
  const queryMatch = trimmed.match(/[?&]node=(\d+)/)
  if (queryMatch) return queryMatch[1]
  return null
}

// ── Marketplace options ───────────────────────────────────────────────────────
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

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "10px 12px",
  borderRadius: 8,
  border: `1px solid ${T.border}`,
  background: T.bg3,
  color: T.text0,
  fontSize: 13,
  fontFamily: T.sans,
  outline: "none",
}

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 11,
  fontWeight: 600,
  color: T.text2,
  marginBottom: 6,
  letterSpacing: ".04em",
  textTransform: "uppercase",
}

export const NodeSearchPage = () => {
  // ── Form state ──────────────────────────────────────────────────────────────
  const [nodeInput, setNodeInput] = useState("")
  const [name, setName] = useState("")
  const [marketplace, setMarketplace] = useState("amazon_us")
  const [top10Alert, setTop10Alert] = useState(true)
  const [hourUtc, setHourUtc] = useState(2)

  // ── UI state ────────────────────────────────────────────────────────────────
  const [submitting, setSubmitting] = useState(false)
  const [created, setCreated] = useState<CategoryTracker[]>([])
  const [error, setError] = useState<string | null>(null)

  // ── Derive parsed node ID for preview ───────────────────────────────────────
  const parsedNodeId = parseNodeId(nodeInput)
  const isUrl = nodeInput.trim().startsWith("http")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!nodeInput.trim()) {
      setError("Please enter a browse node ID or Amazon best-sellers URL.")
      return
    }
    if (!name.trim()) {
      setError("Please enter a tracker name.")
      return
    }

    const scope = isUrl
      ? { browse_node_url: nodeInput.trim(), browse_node_id: parsedNodeId ?? undefined }
      : { browse_node_id: nodeInput.trim() }

    const payload: CategoryTrackerCreateRequest = {
      name: name.trim(),
      marketplace,
      scope,
      tracking_config: { top10_alert_enabled: top10Alert },
      schedule: { frequency: "DAILY", hour_utc: hourUtc },
    }

    setSubmitting(true)
    try {
      const tracker = await apiCreateCategoryTracker(payload)
      setCreated(prev => [tracker, ...prev])
      // Reset form
      setNodeInput("")
      setName("")
      setMarketplace("amazon_us")
      setTop10Alert(true)
      setHourUtc(2)
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setError("A tracker for this marketplace and node already exists.")
        } else if (err.status === 400 && err.details?.reason) {
          setError(err.details.reason)
        } else {
          setError(err.message || "Failed to create tracker. Please try again.")
        }
      } else {
        setError("Failed to create tracker. Please try again.")
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="anim-fade">
      <PageHeader
        title="Node Search"
        sub="Create a Category Tracker by entering an Amazon browse node ID or best-sellers URL"
      />

      {/* ── Form card ─────────────────────────────────────────────────────── */}
      <div className="card" style={{ padding: "24px 24px", marginBottom: 24, maxWidth: 640 }}>
        <form onSubmit={handleSubmit}>
          {/* Browse node input */}
          <div style={{ marginBottom: 18 }}>
            <label style={labelStyle}>Browse Node ID or Best-sellers URL</label>
            <div style={{ position: "relative" }}>
              <Search size={14} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: T.text3, pointerEvents: "none" }} />
              <input
                type="text"
                value={nodeInput}
                onChange={e => setNodeInput(e.target.value)}
                placeholder="e.g. 13893610011 or https://www.amazon.com/Best-Sellers/zgbs/..."
                style={{ ...inputStyle, paddingLeft: 34 }}
              />
            </div>
            {/* Parse preview */}
            {nodeInput.trim() && (
              <div style={{ marginTop: 6, display: "flex", alignItems: "center", gap: 6 }}>
                {parsedNodeId ? (
                  <>
                    <CheckCircle size={12} style={{ color: T.green }} />
                    <span style={{ fontSize: 11, color: T.green, fontFamily: T.mono }}>
                      Node ID: {parsedNodeId}
                    </span>
                  </>
                ) : (
                  <>
                    <AlertCircle size={12} style={{ color: T.red }} />
                    <span style={{ fontSize: 11, color: T.red }}>
                      Could not extract node ID — check the URL format
                    </span>
                  </>
                )}
                {isUrl && (
                  <a
                    href={nodeInput.trim()}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ fontSize: 11, color: T.blue, marginLeft: 8, display: "inline-flex", alignItems: "center", gap: 3, textDecoration: "none" }}
                  >
                    Preview <ExternalLink size={10} />
                  </a>
                )}
              </div>
            )}
          </div>

          {/* Name */}
          <div style={{ marginBottom: 18 }}>
            <label style={labelStyle}>Tracker Name</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="e.g. Baby Bottle Warmers - US"
              maxLength={120}
              style={inputStyle}
            />
          </div>

          {/* Marketplace */}
          <div style={{ marginBottom: 18 }}>
            <label style={labelStyle}>Marketplace</label>
            <select
              value={marketplace}
              onChange={e => setMarketplace(e.target.value)}
              style={{ ...inputStyle, cursor: "pointer" }}
            >
              {MARKETPLACES.map(m => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>

          {/* Schedule & config row */}
          <div style={{ display: "flex", gap: 16, marginBottom: 22, flexWrap: "wrap" }}>
            <div style={{ flex: 1, minWidth: 140 }}>
              <label style={labelStyle}>Run at (UTC hour)</label>
              <select
                value={hourUtc}
                onChange={e => setHourUtc(Number(e.target.value))}
                style={{ ...inputStyle, cursor: "pointer" }}
              >
                {Array.from({ length: 24 }, (_, i) => (
                  <option key={i} value={i}>{String(i).padStart(2, "0")}:00 UTC</option>
                ))}
              </select>
            </div>

            <div style={{ flex: 1, minWidth: 160, display: "flex", flexDirection: "column", justifyContent: "flex-end" }}>
              <label style={labelStyle}>Top 10 Alerts</label>
              <button
                type="button"
                onClick={() => setTop10Alert(v => !v)}
                style={{
                  padding: "10px 12px",
                  borderRadius: 8,
                  border: `1px solid ${top10Alert ? T.amber : T.border}`,
                  background: top10Alert ? T.bg4 : T.bg3,
                  color: top10Alert ? T.amber : T.text2,
                  fontSize: 13,
                  fontFamily: T.sans,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  transition: "all .15s",
                }}
              >
                <span style={{
                  width: 14, height: 14, borderRadius: "50%",
                  background: top10Alert ? T.amber : T.text3,
                  display: "inline-block", flexShrink: 0,
                }} />
                {top10Alert ? "Enabled" : "Disabled"}
              </button>
            </div>
          </div>

          {/* Error banner */}
          {error && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 12px", borderRadius: 8, background: `${T.red}18`, border: `1px solid ${T.red}40`, marginBottom: 16 }}>
              <AlertCircle size={14} style={{ color: T.red, flexShrink: 0 }} />
              <span style={{ fontSize: 13, color: T.red }}>{error}</span>
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={submitting}
            style={{
              width: "100%",
              padding: "11px 0",
              borderRadius: 8,
              border: "none",
              background: submitting ? T.bg4 : `linear-gradient(135deg, ${T.amber} 0%, ${T.amberD} 100%)`,
              color: submitting ? T.text3 : T.bg0,
              fontSize: 14,
              fontWeight: 700,
              fontFamily: T.sans,
              cursor: submitting ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              transition: "all .15s",
            }}
          >
            <Plus size={15} />
            {submitting ? "Creating tracker…" : "Create Category Tracker"}
          </button>
        </form>
      </div>

      {/* ── Created trackers list ─────────────────────────────────────────── */}
      {created.length > 0 && (
        <>
          <div style={{ fontSize: 13, fontWeight: 600, color: T.text1, marginBottom: 12 }}>
            Created this session ({created.length})
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10, maxWidth: 640 }}>
            {created.map(t => (
              <div key={t.tracker_code} className="card" style={{ padding: "14px 18px", borderLeft: `3px solid ${T.green}` }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                      <CheckCircle size={13} style={{ color: T.green }} />
                      <span style={{ fontSize: 14, fontWeight: 700, color: T.text0 }}>{t.name}</span>
                      <Badge type="top10" text={t.marketplace.toUpperCase()} />
                    </div>
                    <div style={{ fontSize: 11, color: T.text3, fontFamily: T.mono }}>
                      Code: <strong style={{ color: T.amber }}>{t.tracker_code}</strong>
                      {" · "}
                      Node: <strong style={{ color: T.blue }}>{t.scope.browse_node_id ?? "—"}</strong>
                      {" · "}
                      {t.schedule.frequency} @ {String(t.schedule.hour_utc).padStart(2, "0")}:00 UTC
                      {" · "}
                      Top 10 alerts: {t.tracking_config.top10_alert_enabled ? "ON" : "OFF"}
                    </div>
                  </div>
                  {t.scope.browse_node_url && (
                    <a
                      href={t.scope.browse_node_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ fontSize: 11, color: T.blue, display: "inline-flex", alignItems: "center", gap: 4, textDecoration: "none" }}
                    >
                      Browse <ExternalLink size={10} />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
