"use client"

import { useState, useEffect } from "react"
import { Play, RefreshCw, CheckCircle, XCircle, Clock, Loader, AlertTriangle } from "lucide-react"
import { T } from "../shared/DesignTokens"
import { PageHeader } from "../shared/PageHeader"
import { Badge } from "../shared/Badge"
import { apiListJobs, apiTriggerJob } from "../shared/api"
import type { Job, JobStatus } from "../shared/types"

const STATUS_META: Record<JobStatus, { color: string; icon: React.ReactNode }> = {
  QUEUED: { color: T.text2, icon: <Clock size={12} /> },
  DISPATCHING: { color: T.amber, icon: <Loader size={12} /> },
  RUNNING_EXTERNAL: { color: T.blue, icon: <Loader size={12} /> },
  IMPORTING: { color: T.blue, icon: <Loader size={12} /> },
  PROCESSING: { color: T.teal, icon: <Loader size={12} /> },
  SUCCESS: { color: T.green, icon: <CheckCircle size={12} /> },
  PARTIAL_SUCCESS: { color: T.amber, icon: <AlertTriangle size={12} /> },
  FAILED: { color: T.red, icon: <XCircle size={12} /> },
}

export const JobsPage = () => {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [triggering, setTriggering] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadJobs = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await apiListJobs()
      setJobs(res.items)
    } catch {
      setJobs([])
      setError("Failed to load jobs")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadJobs()
  }, [])

  const handleTrigger = async (trackerType: "CATEGORY" | "COMPETITOR", trackerCode: string) => {
    setTriggering(true)
    setError(null)
    try {
      const newJob = await apiTriggerJob(trackerType, trackerCode)
      setJobs(prev => [newJob, ...prev])
    } catch {
      setError("Failed to trigger job")
    } finally {
      setTriggering(false)
    }
  }

  const formatDuration = (start?: string | null, end?: string | null): string => {
    if (!start || !end) return "—"
    const ms = new Date(end).getTime() - new Date(start).getTime()
    if (ms < 60000) return `${Math.round(ms / 1000)}s`
    return `${Math.round(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`
  }

  return (
    <div className="anim-fade">
      <PageHeader title="Jobs" sub="Scrape job history and manual triggers"
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn-ghost" onClick={loadJobs}><RefreshCw size={14} /> Refresh</button>
            <button className="btn-primary" onClick={() => handleTrigger("CATEGORY", "ct_baby_bottle_warmers_us")} disabled={triggering}>
              <Play size={14} /> {triggering ? "Queuing..." : "Trigger Category Job"}
            </button>
          </div>
        } />

      {error && (
        <div style={{ marginBottom: 12, color: T.red, fontSize: 12 }}>{error}</div>
      )}

      {loading ? (
        <div style={{ textAlign: "center", padding: 60, color: T.text3 }}>Loading jobs...</div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${T.border}` }}>
                {["Job Code", "Tracker", "Type", "Date", "Trigger", "Status", "Items", "Events", "Duration", "Error"].map(h => (
                  <th key={h} className="th">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {jobs.map(job => {
                const sm = STATUS_META[job.status]
                return (
                  <tr key={job.job_code} className="row-hover" style={{ borderBottom: `1px solid ${T.border}` }}>
                    <td style={{ padding: "9px 12px", fontFamily: T.mono, fontSize: 10, color: T.text3 }}>{job.job_code}</td>
                    <td style={{ padding: "9px 12px", fontSize: 11, color: T.text1 }}>{job.tracker_code}</td>
                    <td style={{ padding: "9px 12px" }}>
                      <Badge type={job.tracker_type === "CATEGORY" ? "top10" : "info"} text={job.tracker_type} />
                    </td>
                    <td style={{ padding: "9px 12px", fontFamily: T.mono, fontSize: 11, color: T.text2 }}>{job.snapshot_date}</td>
                    <td style={{ padding: "9px 12px" }}>
                      <span style={{ fontSize: 10, padding: "2px 6px", borderRadius: 4, fontFamily: T.mono, fontWeight: 600,
                        background: job.trigger_mode === "MANUAL" ? `${T.blue}20` : T.bg4,
                        color: job.trigger_mode === "MANUAL" ? T.blue : T.text2 }}>
                        {job.trigger_mode}
                      </span>
                    </td>
                    <td style={{ padding: "9px 12px" }}>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 10, fontWeight: 600, color: sm.color, fontFamily: T.mono }}>
                        {sm.icon} {job.status}
                      </span>
                    </td>
                    <td style={{ padding: "9px 12px", fontFamily: T.mono, fontSize: 11, color: T.text1 }}>
                      {job.summary.imported_items}/{job.summary.expected_items}
                    </td>
                    <td style={{ padding: "9px 12px", fontFamily: T.mono, fontSize: 11, color: T.amber }}>
                      {job.summary.events_emitted}
                    </td>
                    <td style={{ padding: "9px 12px", fontFamily: T.mono, fontSize: 11, color: T.text2 }}>
                      {formatDuration(job.started_at, job.finished_at)}
                    </td>
                    <td style={{ padding: "9px 12px", fontSize: 11, color: T.red, maxWidth: 200 }}>
                      {job.error ? (
                        <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={job.error.message}>
                          {job.error.code}: {job.error.message}
                        </div>
                      ) : "—"}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {jobs.length === 0 && (
            <div style={{ textAlign: "center", padding: 40, color: T.text3, fontSize: 13 }}>No jobs recorded</div>
          )}
        </div>
      )}
    </div>
  )
}
