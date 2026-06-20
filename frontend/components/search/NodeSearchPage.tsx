"use client"

import { AlertCircle, CheckCircle, ExternalLink, Plus, Search } from "lucide-react"
import { useState } from "react"
import { Badge } from "../shared/Badge"
import { MARKETPLACE_LABELS, T } from "../shared/DesignTokens"
import { PageHeader } from "../shared/PageHeader"
import { apiCreateCategoryTracker } from "../shared/api"
import { MARKETPLACES, parseBestsellerUrl } from "../shared/formatting"
import { handleApiError } from "../shared/hooks"
import type { CategoryTracker, CategoryTrackerCreateRequest } from "../shared/types"

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

  // ── Derive parsed URL for preview ──────────────────────────────────────────
  const parsedUrl = parseBestsellerUrl(nodeInput)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!nodeInput.trim()) {
      setError("Please enter a Best-sellers category URL.")
      return
    }
    if (!parsedUrl) {
      setError("Please enter a valid Amazon Best-sellers URL (e.g. https://www.amazon.com/Best-Sellers/zgbs/...)")
      return
    }
    if (!name.trim()) {
      setError("Please enter a tracker name.")
      return
    }

    const scope = { browse_node_url: parsedUrl }

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
      handleApiError(err, setError, "A tracker for this marketplace and URL already exists.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="anim-fade">
      <PageHeader
        title="Node Search"
        sub="Create a Category Tracker by entering an Amazon best-sellers category URL"
      />

      {/* ── Form card ─────────────────────────────────────────────────────── */}
      <div className="card" style={{ padding: "24px 24px", marginBottom: 24, maxWidth: 640 }}>
        <form onSubmit={handleSubmit}>
          {/* Best-sellers URL input */}
          <div style={{ marginBottom: 18 }}>
            <label className="label">Best-sellers Category URL</label>
            <div style={{ position: "relative" }}>
              <Search size={14} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: T.text3, pointerEvents: "none" }} />
              <input
                type="text"
                value={nodeInput}
                onChange={e => setNodeInput(e.target.value)}
                placeholder="e.g. https://www.amazon.com/Best-Sellers/zgbs/electronics/"
                className="input" style={{ paddingLeft: 34 }}
              />
            </div>
            {/* Parse preview */}
            {nodeInput.trim() && (
              <div style={{ marginTop: 6, display: "flex", alignItems: "center", gap: 6 }}>
                {parsedUrl ? (
                  <>
                    <CheckCircle size={12} style={{ color: T.green }} />
                    <span style={{ fontSize: 11, color: T.green }}>
                      Valid Best-sellers URL
                    </span>
                  </>
                ) : (
                  <>
                    <AlertCircle size={12} style={{ color: T.red }} />
                    <span style={{ fontSize: 11, color: T.red }}>
                      Please enter a valid Amazon Best-sellers URL
                    </span>
                  </>
                )}
                {parsedUrl && (
                  <a
                    href={parsedUrl}
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
            <label className="label">Tracker Name</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="e.g. Baby Bottle Warmers - US"
              maxLength={120}
              className="input"
            />
          </div>

          {/* Marketplace */}
          <div style={{ marginBottom: 18 }}>
            <label className="label">Marketplace</label>
            <select
              value={marketplace}
              onChange={e => setMarketplace(e.target.value)}
              className="input" style={{ cursor: "pointer" }}
            >
              {MARKETPLACES.map(m => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>

          {/* Schedule & config row */}
          <div style={{ display: "flex", gap: 16, marginBottom: 22, flexWrap: "wrap" }}>
            <div style={{ flex: 1, minWidth: 140 }}>
              <label className="label">Run at (UTC hour)</label>
              <select
                value={hourUtc}
                onChange={e => setHourUtc(Number(e.target.value))}
                className="input" style={{ cursor: "pointer" }}
              >
                {Array.from({ length: 24 }, (_, i) => (
                  <option key={i} value={i}>{String(i).padStart(2, "0")}:00 UTC</option>
                ))}
              </select>
            </div>

            <div style={{ flex: 1, minWidth: 160, display: "flex", flexDirection: "column", justifyContent: "flex-end" }}>
              <label className="label">Top 10 Alerts</label>
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
              <div key={t.tracker_code} className="card-soft" style={{ padding: "14px 18px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
                      <CheckCircle size={13} style={{ color: T.green }} />
                      <span style={{ fontSize: 15, fontWeight: 700, color: T.text0 }}>{t.name}</span>
                      <Badge type="top10" text={t.marketplace.toUpperCase()} />
                    </div>
                    {t.scope.browse_node_url && (
                      <a href={t.scope.browse_node_url} target="_blank" rel="noopener noreferrer"
                        style={{ fontSize: 11, color: T.text3, textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 3, marginTop: 2, transition: "color .15s" }}
                        onMouseEnter={e => { (e.currentTarget as HTMLAnchorElement).style.color = T.blue }}
                        onMouseLeave={e => { (e.currentTarget as HTMLAnchorElement).style.color = T.text3 }}>
                        <ExternalLink size={10} /> Category URL
                      </a>
                    )}
                    <div style={{ fontSize: 12, color: T.text2, marginTop: 6 }}>
                      {MARKETPLACE_LABELS[t.marketplace] ?? t.marketplace.replace("amazon_", "").toUpperCase()}
                      {" · "}
                      {t.schedule.frequency.charAt(0) + t.schedule.frequency.slice(1).toLowerCase()}
                      {" at "}
                      {String(t.schedule.hour_utc).padStart(2, "0")}:00 UTC
                      {" · Top 10 alerts: "}
                      {t.tracking_config.top10_alert_enabled ? "ON" : "OFF"}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
