"use client"

import { useState, useEffect, useCallback } from "react"
import { FileText, AlertTriangle, ChevronRight, Filter, ChevronLeft } from "lucide-react"
import { T } from "../shared/DesignTokens"
import { PageHeader } from "../shared/PageHeader"
import { Badge } from "../shared/Badge"
import { AlertTypeMeta } from "../shared/AlertTypeMeta"
import { apiListWeeklyDigests, apiGetWeeklyDigest, apiDownloadWeeklyDigest } from "../shared/api"
import type { WeeklyDigest } from "../shared/types"

type DatePreset = "all" | "4weeks" | "12weeks" | "custom"

const toISODate = (d: Date) => d.toISOString().slice(0, 10)

const presetRange = (preset: DatePreset): { from: string } | null => {
  if (preset === "all" || preset === "custom") return null
  const now = new Date()
  const from = new Date(now)
  if (preset === "4weeks") {
    from.setDate(from.getDate() - 28)
  } else if (preset === "12weeks") {
    from.setDate(from.getDate() - 84)
  }
  return { from: toISODate(from) }
}

const PAGE_SIZE = 10

const isCompleteReportDate = (value: string) => {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false
  const year = Number(value.slice(0, 4))
  return year >= 2000 && year <= 2100
}

export const ReportsPage = () => {
  const [digests, setDigests] = useState<WeeklyDigest[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<WeeklyDigest | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pageNum, setPageNum] = useState(1)
  const [datePreset, setDatePreset] = useState<DatePreset>("all")
  const [customFrom, setCustomFrom] = useState("")

  const loadDigests = useCallback(async (p: number) => {
    setLoading(true)
    setError(null)
    try {
      let weekStart: string | undefined
      if (datePreset === "custom") {
        if (customFrom && !isCompleteReportDate(customFrom)) return
        weekStart = customFrom || undefined
      } else {
        const range = presetRange(datePreset)
        weekStart = range?.from
      }
      const res = await apiListWeeklyDigests({
        week_start: weekStart,
        page: p,
        page_size: PAGE_SIZE,
      })
      setDigests(res.items)
      setTotal(res.total)
      setPageNum(p)
    } catch {
      setDigests([])
      setTotal(0)
      setError("Failed to load reports")
    } finally {
      setLoading(false)
    }
  }, [datePreset, customFrom])

  useEffect(() => {
    void loadDigests(1)
  }, [loadDigests])

  const handleSelect = async (code: string) => {
    setError(null)
    try {
      const d = await apiGetWeeklyDigest(code)
      setSelected(d)
    } catch {
      setSelected(null)
      setError("Failed to load digest detail")
    }
  }

  if (loading) return (
    <div style={{ textAlign: "center", padding: 60, color: T.text3, fontSize: 13 }}>Loading reports…</div>
  )

  if (digests.length === 0) return (
    <div className="anim-fade">
      <PageHeader title="Reports" sub="Weekly digest & threat analysis" />
      <div style={{ textAlign: "center", padding: "80px 24px", color: T.text3 }}>
        <FileText size={40} style={{ margin: "0 auto 16px", opacity: 0.3 }} />
        <div style={{ fontSize: 15, fontWeight: 600, color: T.text1, marginBottom: 6 }}>No reports yet</div>
        <div style={{ fontSize: 12, color: T.text3 }}>
          {error ?? "Weekly digests are generated automatically once your trackers have collected data."}
        </div>
      </div>
    </div>
  )

  return (
    <div className="anim-fade">
      <PageHeader title="Reports" sub="Weekly digest & threat analysis" />

      {/* Date range filter */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap", alignItems: "center" }}>
        <Filter size={13} style={{ color: T.text3 }} />
        <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
          {(["all", "4weeks", "12weeks", "custom"] as DatePreset[]).map(p => (
            <button key={p} onClick={() => setDatePreset(p)}
              style={{ padding: "5px 10px", borderRadius: 6, border: `1px solid ${datePreset === p ? T.blue : T.border}`, background: datePreset === p ? T.bg4 : T.bg2, color: datePreset === p ? T.blue : T.text2, fontSize: 11, fontWeight: 600, cursor: "pointer", transition: "all .15s" }}>
              {p === "all" ? "All time" : p === "4weeks" ? "Last 4 weeks" : p === "12weeks" ? "Last 12 weeks" : "Custom"}
            </button>
          ))}
          {datePreset === "custom" && (
            <>
              <input type="date" value={customFrom} onChange={e => setCustomFrom(e.target.value)}
                style={{ padding: "4px 8px", borderRadius: 6, border: `1px solid ${T.border}`, background: T.bg2, color: T.text0, fontSize: 11, fontFamily: "monospace", cursor: "pointer" }} />
              <span style={{ color: T.text3, fontSize: 11 }}>from</span>
            </>
          )}
        </div>
      </div>

      {error && (
        <div style={{ marginBottom: 12, color: T.red, fontSize: 12 }}>{error}</div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 16 }}>
        {/* Digest list */}
        <div>
          <div style={{ fontSize: 10, fontWeight: 600, color: T.text3, letterSpacing: ".08em", textTransform: "uppercase", marginBottom: 8, padding: "0 4px", display: "flex", justifyContent: "space-between" }}>
            <span>{digests.length} of {total} Digests</span>
            {loading && <span style={{ fontSize: 9, color: T.text3 }}>Loading…</span>}
          </div>
          {digests.map(d => (
            <div key={d.digest_code} className="row-hover" onClick={() => handleSelect(d.digest_code)}
              style={{ padding: "12px 14px", borderRadius: 8, marginBottom: 4, background: selected?.digest_code === d.digest_code ? T.bg4 : T.bg2, border: `1px solid ${selected?.digest_code === d.digest_code ? T.border2 : T.border}`, cursor: "pointer", transition: "all .15s" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                <FileText size={13} style={{ color: T.amber }} />
                <span style={{ fontSize: 12, fontWeight: 600, color: T.text0 }}>{d.week_start} → {d.week_end}</span>
              </div>
              <div style={{ display: "flex", gap: 8, fontSize: 10, fontFamily: T.mono, color: T.text2 }}>
                <span>{d.summary.new_entrant_count} new</span>
                <span>{d.summary.price_change_count} price</span>
                <span>{d.threats.length} threats</span>
              </div>
              <div style={{ fontSize: 9, fontFamily: T.mono, color: T.text3, marginTop: 4 }}>
                {d.tracker_refs.map(t => t.tracker_name).join(" · ")}
              </div>
            </div>
          ))}
          {digests.length === 0 && (
            <div style={{ textAlign: "center", padding: 40, color: T.text3, fontSize: 12 }}>No digests available</div>
          )}

          {/* Pagination */}
          {total > PAGE_SIZE && (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, marginTop: 16, padding: "8px 0" }}>
              <button onClick={() => loadDigests(pageNum - 1)} disabled={pageNum === 1}
                style={{ padding: "4px 8px", borderRadius: 4, border: `1px solid ${T.border}`, background: T.bg2, color: T.text2, fontSize: 11, cursor: pageNum === 1 ? "default" : "pointer", opacity: pageNum === 1 ? 0.5 : 1 }}>
                <ChevronLeft size={12} />
              </button>
              <span style={{ fontSize: 10, color: T.text3 }}>{pageNum} / {Math.ceil(total / PAGE_SIZE)}</span>
              <button onClick={() => loadDigests(pageNum + 1)} disabled={pageNum >= Math.ceil(total / PAGE_SIZE)}
                style={{ padding: "4px 8px", borderRadius: 4, border: `1px solid ${T.border}`, background: T.bg2, color: T.text2, fontSize: 11, cursor: pageNum >= Math.ceil(total / PAGE_SIZE) ? "default" : "pointer", opacity: pageNum >= Math.ceil(total / PAGE_SIZE) ? 0.5 : 1 }}>
                <ChevronRight size={12} />
              </button>
            </div>
          )}
        </div>

        {/* Detail panel */}
        {selected ? (
          <div className="anim-slide">
            <div className="card" style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: T.text0, marginBottom: 4 }}>
                Weekly Digest — {selected.week_start} to {selected.week_end}
              </div>
              <div style={{ fontSize: 10, fontFamily: T.mono, color: T.text3, marginBottom: 14 }}>
                Code: {selected.digest_code} · Created: {new Date(selected.created_at).toLocaleString()}
              </div>

              {/* Summary KPIs */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 10, marginBottom: 20 }}>
                {[
                  { l: "New Entrants", v: selected.summary.new_entrant_count, c: T.green },
                  { l: "Returning", v: selected.summary.returning_count, c: "#90EE90" },
                  { l: "Top 10 Entry", v: selected.summary.top10_enter_count, c: T.amber },
                  { l: "Price Changes", v: selected.summary.price_change_count, c: T.blue },
                  { l: "Listing Changes", v: selected.summary.listing_change_count, c: T.purple },
                ].map(k => (
                  <div key={k.l} style={{ textAlign: "center", padding: 12, background: T.bg3, borderRadius: 8, border: `1px solid ${T.border}` }}>
                    <div style={{ fontSize: 22, fontWeight: 700, fontFamily: T.mono, color: k.c }}>{k.v}</div>
                    <div style={{ fontSize: 9, color: T.text2, marginTop: 4 }}>{k.l}</div>
                  </div>
                ))}
              </div>

              {/* Tracker Refs */}
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: T.text3, marginBottom: 8, textTransform: "uppercase", letterSpacing: ".04em" }}>Trackers Included</div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {selected.tracker_refs.map(tr => (
                    <span key={tr.tracker_code} style={{ display: "inline-flex", alignItems: "center", gap: 4, padding: "4px 10px", background: T.bg4, border: `1px solid ${T.border}`, borderRadius: 6, fontSize: 11, color: T.text1 }}>
                      {tr.tracker_type === "CATEGORY" ? "📊" : "🎯"} {tr.tracker_name}
                    </span>
                  ))}
                </div>
              </div>

              {/* Download Buttons */}
              <div
                style={{
                  display: "flex",
                  gap: 8,
                  marginBottom: 16,
                }}
              >
                <button
                  onClick={() =>
                    apiDownloadWeeklyDigest(selected.digest_code, "pdf")
                  }
                  style={{
                    padding: "8px 16px",
                    background: T.amber,
                    border: `1px solid ${T.amberD}`,
                    borderRadius: 6,
                    fontSize: 11,
                    fontWeight: 700,
                    color: "#000",
                    cursor: "pointer",
                    boxShadow: "0 0 0 2px rgba(245,166,35,0.15)",
                  }}
                >
                  Download PDF
                </button>

                <button
                  onClick={() =>
                    apiDownloadWeeklyDigest(selected.digest_code, "excel")
                  }
                  style={{
                    padding: "8px 16px",
                    background: "#0F2A1A",
                    border: `1px solid ${T.greenD}`,
                    borderRadius: 6,
                    fontSize: 11,
                    fontWeight: 700,
                    color: T.green,
                    cursor: "pointer",
                    boxShadow: "0 0 0 2px rgba(34,212,122,0.12)",
                  }}
                >
                  Download Excel
                </button>
              </div>
            </div>

            {/* AI Insights */}
            {selected.insights && (
              <div className="card" style={{ marginBottom: 16 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: T.text1 }}>AI Insights</span>
                  <span style={{ fontSize: 9, padding: "2px 6px", background: T.bg4, borderRadius: 4, color: T.text3, border: `1px solid ${T.border}` }}>AI-Powered</span>
                </div>
                <div style={{ fontSize: 12, color: T.text0, lineHeight: 1.6, marginBottom: 12 }}>
                  {selected.insights.executive_summary}
                </div>
                <div style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: 10, fontWeight: 600, color: T.text2, marginBottom: 6, textTransform: "uppercase" as const, letterSpacing: ".04em" }}>Key Trends</div>
                  {selected.insights.key_trends.map((trend, i) => (
                    <div key={i} style={{ fontSize: 11, color: T.text1, marginBottom: 4, paddingLeft: 12, position: "relative" as const, lineHeight: 1.5 }}>
                      <span style={{ position: "absolute", left: 0, color: T.text3 }}>•</span>
                      {trend}
                    </div>
                  ))}
                </div>
                <div>
                  <div style={{ fontSize: 10, fontWeight: 600, color: T.text2, marginBottom: 4, textTransform: "uppercase" as const, letterSpacing: ".04em" }}>Risk Assessment</div>
                  <div style={{ fontSize: 11, color: T.text1, lineHeight: 1.5 }}>
                    {selected.insights.risk_assessment}
                  </div>
                </div>
              </div>
            )}

            {/* Threats */}
            <div className="card">
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
                <AlertTriangle size={14} style={{ color: T.red }} />
                <span style={{ fontSize: 13, fontWeight: 600, color: T.text1 }}>Threats ({selected.threats.length})</span>
              </div>
              {selected.threats.length === 0 && (
                <div style={{ textAlign: "center", padding: "30px 0", color: T.text3, fontSize: 12 }}>No threats detected this week</div>
              )}
              {selected.threats.map((threat, i) => (
                <div key={i} style={{ padding: "14px 0", borderBottom: i < selected.threats.length - 1 ? `1px solid ${T.border}` : "none" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                    <span style={{ fontFamily: T.mono, fontSize: 12, color: T.amber, fontWeight: 700 }}>{threat.asin}</span>
                    <span style={{ fontSize: 10, fontFamily: T.mono, color: T.text3 }}>{threat.marketplace}</span>
                  </div>
                  <div style={{ fontSize: 12, color: T.text0, marginBottom: 8, lineHeight: 1.5 }}>{threat.reason}</div>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 6 }}>
                    {threat.event_types?.map(et => {
                      const meta = AlertTypeMeta(et)
                      return <Badge key={et} type={meta.badgeType} text={meta.label} />
                    })}
                  </div>
                  <div style={{ display: "flex", gap: 8, fontSize: 10, color: T.text3 }}>
                    {threat.tracker_refs.map(tr => (
                      <span key={tr.tracker_code}>{tr.tracker_type === "CATEGORY" ? "📊" : "🎯"} {tr.tracker_name}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: 60, color: T.text3, fontSize: 13 }}>
            <ChevronRight size={14} style={{ marginRight: 6 }} /> Select a digest to view details
          </div>
        )}
      </div>
    </div>
  )
}
