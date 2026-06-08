"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { ChevronLeft, ChevronRight, Filter, Settings, Plus, Trash2, ChevronDown, X } from "lucide-react"
import { T } from "../shared/DesignTokens"
import { PageHeader } from "../shared/PageHeader"
import { Badge } from "../shared/Badge"
import { AlertTypeMeta } from "../shared/AlertTypeMeta"
import {
  apiCreateNotificationRule,
  apiDeleteNotificationRule,
  apiGetProductDetail,
  apiListCategoryTrackers,
  apiListCompetitorTrackers,
  apiListEvents,
  apiListNotificationRules,
  apiUpdateNotificationRule,
} from "../shared/api"
import type { Event, EventType, Severity, CategoryTracker, CompetitorTracker, NotificationRule, NotificationRuleRequest } from "../shared/types"

const EVENT_TYPES: EventType[] = [
  "NEW_ENTRANT_TOP50", "RETURNING_TOP50", "EXIT_TOP50",
  "ENTER_TOP10", "EXIT_TOP10",
  "PRICE_CHANGED", "PROMOTION_CHANGED",
  "TITLE_CHANGED", "MAIN_IMAGE_CHANGED", "VARIATIONS_ADDED",
  "AVAILABILITY_CHANGED", "BUY_BOX_CHANGED",
]
const SEVERITIES: Severity[] = ["HIGH", "MEDIUM", "LOW"]

type DatePreset = "all" | "today" | "7d" | "30d" | "custom"

const toISODate = (d: Date) => d.toISOString().slice(0, 10)

const presetRange = (preset: DatePreset): { from: string; to: string } | null => {
  if (preset === "all" || preset === "custom") return null
  const now = new Date()
  const to = toISODate(now)
  if (preset === "today") return { from: to, to }
  const from = new Date(now)
  from.setDate(from.getDate() - (preset === "7d" ? 7 : 30))
  return { from: toISODate(from), to }
}

// Notification Rules

type EditableNotificationRule = {
  rule_code: string
  name: string
  enabled: boolean
  severities: Severity[]
  event_types: EventType[]
  tracker_type: "" | "CATEGORY" | "COMPETITOR" | "KEYWORD"
  tracker_code: string
  webhook_url: string
}

const makeNewRule = (): EditableNotificationRule => ({
  rule_code: "new",
  name: "New Rule",
  enabled: true,
  severities: ["HIGH"],
  event_types: [],
  tracker_type: "",
  tracker_code: "",
  webhook_url: "",
})

const toEditableRule = (rule: NotificationRule): EditableNotificationRule => ({
  rule_code: rule.rule_code,
  name: rule.name,
  enabled: rule.enabled,
  severities: rule.severities,
  event_types: rule.event_types,
  tracker_type: rule.tracker_type || "",
  tracker_code: rule.tracker_code || "",
  webhook_url: rule.webhook_url,
})

const toRuleRequest = (rule: EditableNotificationRule): NotificationRuleRequest => {
  return {
    name: rule.name,
    enabled: rule.enabled,
    webhook_url: rule.webhook_url,
    severities: rule.severities,
    event_types: rule.event_types,
    tracker_type: rule.tracker_type || null,
    tracker_code: rule.tracker_code || null,
  }
}

// TrackerDropdown

interface TrackerDropdownProps {
  label: string
  options: { code: string; name: string }[]
  selectedCode: string
  onSelect: (code: string) => void
}

const TrackerDropdown = ({ label, options, selectedCode, onSelect }: TrackerDropdownProps) => {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState("")
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    if (open) document.addEventListener("mousedown", handler)
    return () => document.removeEventListener("mousedown", handler)
  }, [open])

  const selected = selectedCode ? options.find(o => o.code === selectedCode) : null
  const filtered = search ? options.filter(o => o.name.toLowerCase().includes(search.toLowerCase())) : options

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        onClick={() => setOpen(v => !v)}
        style={{
          display: "flex", alignItems: "center", gap: 5,
          padding: "5px 10px", borderRadius: 6,
          border: `1px solid ${selected ? T.blue : T.border}`,
          background: selected ? T.bg4 : T.bg2,
          color: selected ? T.blue : T.text2,
          fontSize: 11, fontWeight: 600, cursor: "pointer", transition: "all .15s",
          maxWidth: 170, whiteSpace: "nowrap", overflow: "hidden",
        }}
      >
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", flex: 1, textAlign: "left" }}>
          {selected ? selected.name : label}
        </span>
        {selected ? (
          <X
            size={10}
            onClick={e => { e.stopPropagation(); onSelect(""); setOpen(false); setSearch("") }}
            style={{ flexShrink: 0, opacity: 0.7 }}
          />
        ) : (
          <ChevronDown size={10} style={{ flexShrink: 0 }} />
        )}
      </button>

      {open && (
        <div style={{
          position: "absolute", top: "calc(100% + 4px)", left: 0, zIndex: 200,
          background: T.bg2, border: `1px solid ${T.border}`, borderRadius: 8,
          minWidth: 220, maxHeight: 260, display: "flex", flexDirection: "column",
          boxShadow: `0 6px 20px ${T.bg0}CC`,
        }}>
          <div style={{ padding: "6px 8px", borderBottom: `1px solid ${T.border}` }}>
            <input
              type="text"
              placeholder="Search..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              autoFocus
              style={{
                width: "100%", padding: "5px 8px", borderRadius: 4,
                border: `1px solid ${T.border}`, background: T.bg3,
                color: T.text0, fontSize: 11, outline: "none",
              }}
            />
          </div>
          <div style={{ overflowY: "auto", flex: 1 }}>
            <button
              onClick={() => { onSelect(""); setOpen(false); setSearch("") }}
              style={{
                width: "100%", padding: "8px 12px", background: !selectedCode ? `${T.blue}20` : "transparent",
                color: !selectedCode ? T.blue : T.text3, border: "none", textAlign: "left",
                fontSize: 11, cursor: "pointer", borderBottom: `1px solid ${T.border}`, transition: "all .15s",
              }}
            >
              All
            </button>
            {filtered.length === 0 && (
              <div style={{ padding: "10px 12px", fontSize: 11, color: T.text3 }}>No results</div>
            )}
            {filtered.map(o => (
              <button
                key={o.code}
                onClick={() => { onSelect(o.code); setOpen(false); setSearch("") }}
                style={{
                  width: "100%", padding: "8px 12px",
                  background: selectedCode === o.code ? `${T.blue}20` : "transparent",
                  color: selectedCode === o.code ? T.blue : T.text2,
                  border: "none", textAlign: "left", fontSize: 11, cursor: "pointer",
                  transition: "all .15s", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                }}
              >
                {o.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// RuleEditor

interface RuleEditorProps {
  rule: EditableNotificationRule
  onChange: (patch: Partial<EditableNotificationRule>) => void
  onSave: () => void
  onCancel: () => void
  categoryTrackers: CategoryTracker[]
  competitorTrackers: CompetitorTracker[]
}

const RuleEditor = ({ rule, onChange, onSave, onCancel, categoryTrackers, competitorTrackers }: RuleEditorProps) => {
  const toggleSeverity = (s: Severity) => {
    const next = rule.severities.includes(s)
      ? rule.severities.filter(x => x !== s)
      : [...rule.severities, s]
    onChange({ severities: next })
  }

  const toggleEventType = (et: EventType) => {
    const next = rule.event_types.includes(et)
      ? rule.event_types.filter(x => x !== et)
      : [...rule.event_types, et]
    onChange({ event_types: next })
  }

  const trackerOptions =
    rule.tracker_type === "CATEGORY"
      ? categoryTrackers.map(t => ({ code: t.tracker_code, name: t.name }))
      : rule.tracker_type === "COMPETITOR"
        ? competitorTrackers.map(t => ({ code: t.tracker_code, name: t.name }))
        : []

  return (
    <div style={{
      padding: "14px 16px", background: T.bg3, borderTop: `1px solid ${T.border}`,
      display: "flex", flexDirection: "column", gap: 12,
    }}>
      {/* Name + Webhook */}
      <div style={{ display: "flex", gap: 10 }}>
        <div style={{ flex: "0 0 180px" }}>
          <div style={{ fontSize: 10, fontWeight: 600, color: T.text3, marginBottom: 4 }}>RULE NAME</div>
          <input
            value={rule.name}
            onChange={e => onChange({ name: e.target.value })}
            style={{
              width: "100%", padding: "6px 10px", borderRadius: 4,
              border: `1px solid ${T.border}`, background: T.bg4,
              color: T.text0, fontSize: 12, outline: "none",
            }}
          />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 10, fontWeight: 600, color: T.text3, marginBottom: 4 }}>SLACK WEBHOOK URL</div>
          <input
            value={rule.webhook_url}
            onChange={e => onChange({ webhook_url: e.target.value })}
            placeholder="https://hooks.slack.com/services/..."
            style={{
              width: "100%", padding: "6px 10px", borderRadius: 4,
              border: `1px solid ${rule.webhook_url ? T.green : T.border}`,
              background: T.bg4, color: T.text0, fontSize: 11, fontFamily: T.mono, outline: "none",
            }}
          />
        </div>
      </div>

      {/* Severity */}
      <div>
        <div style={{ fontSize: 10, fontWeight: 600, color: T.text3, marginBottom: 6 }}>
          SEVERITY - leave empty to match all
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          {SEVERITIES.map(s => {
            const active = rule.severities.includes(s)
            const col = s === "HIGH" ? T.red : s === "MEDIUM" ? T.amber : T.green
            return (
              <button
                key={s}
                onClick={() => toggleSeverity(s)}
                style={{
                  padding: "4px 10px", borderRadius: 5,
                  border: `1px solid ${active ? col : T.border}`,
                  background: active ? `${col}22` : "transparent",
                  color: active ? col : T.text3,
                  fontSize: 11, fontWeight: 600, cursor: "pointer", transition: "all .15s",
                }}
              >
                {s}
              </button>
            )
          })}
        </div>
      </div>

      {/* Event types */}
      <div>
        <div style={{ fontSize: 10, fontWeight: 600, color: T.text3, marginBottom: 6 }}>
          EVENT TYPES - leave empty to match all
        </div>
        <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
          {EVENT_TYPES.map(et => {
            const meta = AlertTypeMeta(et)
            const active = rule.event_types.includes(et)
            return (
              <button
                key={et}
                onClick={() => toggleEventType(et)}
                style={{
                  display: "flex", alignItems: "center", gap: 4,
                  padding: "4px 8px", borderRadius: 5,
                  border: `1px solid ${active ? meta.color : T.border}`,
                  background: active ? `${meta.color}22` : "transparent",
                  color: active ? meta.color : T.text3,
                  fontSize: 10, cursor: "pointer", transition: "all .15s",
                }}
              >
                <span style={{ display: "flex" }}>{meta.icon}</span>
                <span style={{ fontFamily: T.mono }}>{meta.label}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Tracker filter */}
      <div>
        <div style={{ fontSize: 10, fontWeight: 600, color: T.text3, marginBottom: 6 }}>
          TRACKER FILTER - leave empty to match all
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <div style={{ display: "flex", gap: 4 }}>
            {([
              { value: "" as const, label: "All" },
              { value: "CATEGORY" as const, label: "Category" },
              { value: "COMPETITOR" as const, label: "Competitor" },
            ] as const).map(opt => (
              <button
                key={opt.value}
                onClick={() => onChange({ tracker_type: opt.value, tracker_code: "" })}
                style={{
                  padding: "4px 10px", borderRadius: 5,
                  border: `1px solid ${rule.tracker_type === opt.value ? T.blue : T.border}`,
                  background: rule.tracker_type === opt.value ? `${T.blue}22` : "transparent",
                  color: rule.tracker_type === opt.value ? T.blue : T.text3,
                  fontSize: 11, fontWeight: 600, cursor: "pointer", transition: "all .15s",
                }}
              >
                {opt.label}
              </button>
            ))}
          </div>
          {rule.tracker_type && (
            <TrackerDropdown
              label={`${rule.tracker_type === "CATEGORY" ? "Category" : "Competitor"}: All`}
              options={trackerOptions}
              selectedCode={rule.tracker_code}
              onSelect={code => onChange({ tracker_code: code })}
            />
          )}
        </div>
      </div>

      {/* Actions */}
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <button
          onClick={onCancel}
          style={{
            padding: "6px 14px", borderRadius: 5, border: `1px solid ${T.border}`,
            background: "transparent", color: T.text2, fontSize: 11, cursor: "pointer",
          }}
        >
          Cancel
        </button>
        <button
          onClick={onSave}
          style={{
            padding: "6px 14px", borderRadius: 5, border: `1px solid ${T.green}`,
            background: T.green, color: T.bg0, fontSize: 11, fontWeight: 600, cursor: "pointer",
          }}
        >
          Save Rule
        </button>
      </div>
    </div>
  )
}

export const EventsPage = () => {
  const [events, setEvents] = useState<Event[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPageNum] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filterType, setFilterType] = useState<EventType | "">("")
  const [filterSeverity, setFilterSeverity] = useState<Severity | "">("")
  const [datePreset, setDatePreset] = useState<DatePreset>("all")
  const [customFrom, setCustomFrom] = useState("")
  const [customTo, setCustomTo] = useState("")
  const [productImages, setProductImages] = useState<Map<string, string>>(new Map())
  const [filterTrackerType, setFilterTrackerType] = useState<"" | "CATEGORY" | "COMPETITOR" | "KEYWORD">("")
  const [selectedTrackerCode, setSelectedTrackerCode] = useState<string>("")
  const [categoryTrackers, setCategoryTrackers] = useState<CategoryTracker[]>([])
  const [competitorTrackers, setCompetitorTrackers] = useState<CompetitorTracker[]>([])

  // Notification settings
  const [showSettings, setShowSettings] = useState(false)
  const [notifRules, setNotifRules] = useState<NotificationRule[]>([])
  const [expandedRuleId, setExpandedRuleId] = useState<string | null>(null)
  const [editingRules, setEditingRules] = useState<Record<string, EditableNotificationRule>>({})

  const loadNotificationRules = useCallback(async () => {
    try {
      setNotifRules(await apiListNotificationRules())
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    void loadNotificationRules()
  }, [loadNotificationRules])
  const loadEvents = useCallback(async (p: number) => {
    setLoading(true)
    setError(null)
    try {
      let fromDate: string | undefined
      let toDate: string | undefined
      if (datePreset === "custom") {
        fromDate = customFrom || undefined
        toDate = customTo || undefined
      } else {
        const range = presetRange(datePreset)
        fromDate = range?.from
        toDate = range?.to
      }
      const res = await apiListEvents({
        event_type: filterType || undefined,
        severity: filterSeverity || undefined,
        tracker_type: filterTrackerType || undefined,
        tracker_code: selectedTrackerCode || undefined,
        from_date: fromDate,
        to_date: toDate,
        page: p,
        page_size: 20,
      })
      setEvents(res.items)
      setTotal(res.total)
      setPageNum(p)

      // Batch-fetch product images for unique ASINs on this page
      const pairs = [...new Map(res.items.map(e => [`${e.marketplace}:${e.asin}`, e])).values()]
      const results = await Promise.allSettled(
        pairs.map(e => apiGetProductDetail(e.marketplace, e.asin))
      )
      const imgMap = new Map<string, string>()
      results.forEach((r, i) => {
        if (r.status === "fulfilled" && r.value?.main_image_url_latest) {
          imgMap.set(`${pairs[i].marketplace}:${pairs[i].asin}`, r.value.main_image_url_latest)
        }
      })
      setProductImages(imgMap)
    } catch {
      setEvents([])
      setTotal(0)
      setPageNum(p)
      setError("Failed to load events")
    } finally {
      setLoading(false)
    }
  }, [filterType, filterSeverity, filterTrackerType, selectedTrackerCode, datePreset, customFrom, customTo])

  useEffect(() => {
    void loadEvents(1)
  }, [loadEvents])

  useEffect(() => {
    void Promise.all([
      apiListCategoryTrackers().then(res => setCategoryTrackers(res.items)),
      apiListCompetitorTrackers().then(res => setCompetitorTrackers(res.items)),
    ])
  }, [])

  // Active trackers for filter dropdowns (only ACTIVE status)
  const activeCategoryOptions = categoryTrackers
    .filter(t => t.status === "ACTIVE")
    .map(t => ({ code: t.tracker_code, name: t.name }))

  const activeCompetitorOptions = competitorTrackers
    .filter(t => t.status === "ACTIVE")
    .map(t => ({ code: t.tracker_code, name: t.name }))

  const selectCategory = (code: string) => {
    setSelectedTrackerCode(code)
    setFilterTrackerType(code ? "CATEGORY" : "")
  }

  const selectCompetitor = (code: string) => {
    setSelectedTrackerCode(code)
    setFilterTrackerType(code ? "COMPETITOR" : "")
  }

  // Rule management helpers
  const addRule = () => {
    const rule = makeNewRule()
    setExpandedRuleId(rule.rule_code)
    setEditingRules(prev => ({ ...prev, [rule.rule_code]: rule }))
  }

  const deleteRule = async (ruleCode: string) => {
    await apiDeleteNotificationRule(ruleCode)
    setNotifRules(prev => prev.filter(r => r.rule_code !== ruleCode))
    if (expandedRuleId === ruleCode) setExpandedRuleId(null)
  }

  const toggleRuleEnabled = async (rule: NotificationRule) => {
    const updated = await apiUpdateNotificationRule(rule.rule_code, { enabled: !rule.enabled })
    setNotifRules(prev => prev.map(r => r.rule_code === rule.rule_code ? updated : r))
  }

  const startEditing = (rule: NotificationRule) => {
    const editable = toEditableRule(rule)
    setEditingRules(prev => ({ ...prev, [rule.rule_code]: editable }))
    setExpandedRuleId(prev => prev === rule.rule_code ? null : rule.rule_code)
  }

  const saveRule = async (ruleCode: string) => {
    const editing = editingRules[ruleCode]
    if (!editing) return
    const saved = ruleCode === "new"
      ? await apiCreateNotificationRule(toRuleRequest(editing))
      : await apiUpdateNotificationRule(ruleCode, toRuleRequest(editing))
    setNotifRules(prev => ruleCode === "new" ? [...prev, saved] : prev.map(r => r.rule_code === ruleCode ? saved : r))
    setExpandedRuleId(null)
    setEditingRules(prev => { const n = { ...prev }; delete n[ruleCode]; return n })
  }

  const cancelEditing = (ruleCode: string) => {
    setExpandedRuleId(null)
    setEditingRules(prev => { const n = { ...prev }; delete n[ruleCode]; return n })
  }

  const updateEditingRule = (ruleCode: string, patch: Partial<EditableNotificationRule>) => {
    setEditingRules(prev => ({ ...prev, [ruleCode]: { ...prev[ruleCode], ...patch } }))
  }

  const displayedRules = expandedRuleId === "new" && editingRules.new ? [...notifRules, editingRules.new] : notifRules
  const activeRuleCount = notifRules.filter(r => r.enabled && r.webhook_url).length

  return (
    <div className="anim-fade">
      <PageHeader
        title="Events"
        sub={`${total} events detected`}
        actions={
          <button
            onClick={() => setShowSettings(v => !v)}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "6px 12px", borderRadius: 6,
              border: `1px solid ${showSettings ? T.blue : T.border}`,
              background: showSettings ? `${T.blue}15` : T.bg2,
              color: showSettings ? T.blue : T.text2,
              fontSize: 11, fontWeight: 600, cursor: "pointer", transition: "all .15s",
            }}
          >
            <Settings size={13} />
            Notify Settings
            {activeRuleCount > 0 && (
              <span style={{
                display: "inline-flex", alignItems: "center", justifyContent: "center",
                minWidth: 17, height: 17, borderRadius: 9, padding: "0 4px",
                background: T.green, color: T.bg0, fontSize: 9, fontWeight: 700,
              }}>
                {activeRuleCount}
              </span>
            )}
          </button>
        }
      />

      {/* Settings Panel */}
      {showSettings && (
        <div style={{
          marginBottom: 20, borderRadius: 10,
          border: `1px solid ${T.border}`, background: T.bg2, overflow: "hidden",
        }}>
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "12px 16px",
            borderBottom: displayedRules.length > 0 ? `1px solid ${T.border}` : undefined,
            background: T.bg3,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Settings size={13} style={{ color: T.text3 }} />
              <span style={{ fontSize: 12, fontWeight: 700, color: T.text1 }}>Notification Rules</span>
              {displayedRules.length > 0 && (
                <span style={{ fontSize: 10, color: T.text3, background: T.bg4, padding: "1px 6px", borderRadius: 4 }}>
                  {displayedRules.length} rule{displayedRules.length > 1 ? "s" : ""}
                </span>
              )}
            </div>
            <button
              onClick={addRule}
              style={{
                display: "flex", alignItems: "center", gap: 5,
                padding: "5px 10px", borderRadius: 5,
                border: `1px solid ${T.blue}`, background: `${T.blue}20`,
                color: T.blue, fontSize: 11, fontWeight: 600, cursor: "pointer",
              }}
            >
              <Plus size={11} /> Add Rule
            </button>
          </div>

          {displayedRules.length === 0 ? (
            <div style={{ padding: "24px 16px", textAlign: "center" }}>
              <div style={{ fontSize: 12, color: T.text3, marginBottom: 4 }}>No notification rules yet</div>
              <div style={{ fontSize: 11, color: T.text3 }}>
                Add a rule to automatically send matching events to a Slack webhook.
              </div>
            </div>
          ) : (
            displayedRules.map((rule, idx) => {
              const ruleCode = rule.rule_code
              const isNewRule = ruleCode === "new"
              const isEditing = expandedRuleId === ruleCode
              const editState = editingRules[ruleCode] || (isNewRule ? rule as EditableNotificationRule : toEditableRule(rule as NotificationRule))
              return (
                <div key={ruleCode} style={{ borderBottom: idx < displayedRules.length - 1 ? `1px solid ${T.border}` : undefined }}>
                  <div style={{
                    display: "flex", alignItems: "center", gap: 10, padding: "10px 16px",
                    background: isEditing ? T.bg3 : undefined,
                  }}>
                    <button
                      onClick={() => isNewRule ? updateEditingRule("new", { enabled: !rule.enabled }) : void toggleRuleEnabled(rule as NotificationRule)}
                      title={rule.enabled ? "Disable" : "Enable"}
                      style={{
                        width: 32, height: 18, borderRadius: 9, border: "none", cursor: "pointer",
                        background: rule.enabled ? T.green : T.border2,
                        position: "relative", flexShrink: 0, transition: "background .2s",
                      }}
                    >
                      <span style={{
                        position: "absolute", top: 2, left: rule.enabled ? 16 : 2,
                        width: 14, height: 14, borderRadius: "50%",
                        background: rule.enabled ? T.bg0 : T.text3, transition: "left .2s",
                      }} />
                    </button>
                    <span style={{
                      fontSize: 12, fontWeight: 600, color: rule.enabled ? T.text1 : T.text3,
                      flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                    }}>
                      {rule.name}
                    </span>
                    <div style={{ display: "flex", gap: 3, flexShrink: 0 }}>
                      {(rule.severities.length > 0 ? rule.severities : ["ALL" as const]).map(s => {
                        const col = s === "HIGH" ? T.red : s === "MEDIUM" ? T.amber : s === "LOW" ? T.green : T.text3
                        return (
                          <span key={s} style={{ fontSize: 9, fontWeight: 700, padding: "1px 5px", borderRadius: 3, border: `1px solid ${col}30`, color: col, background: `${col}15` }}>{s}</span>
                        )
                      })}
                    </div>
                    <span style={{ fontSize: 10, fontFamily: T.mono, color: rule.webhook_url ? T.green : T.red, flexShrink: 0 }}>
                      {rule.webhook_url ? "Webhook" : "No webhook"}
                    </span>
                    {rule.tracker_code && (
                      <span style={{ fontSize: 9, padding: "1px 5px", borderRadius: 3, background: T.bg4, color: T.text3, fontFamily: T.mono, flexShrink: 0 }}>
                        {[...categoryTrackers, ...competitorTrackers].find(t => t.tracker_code === rule.tracker_code)?.name || rule.tracker_code}
                      </span>
                    )}
                    <button
                      onClick={() => isNewRule ? setExpandedRuleId("new") : startEditing(rule as NotificationRule)}
                      style={{
                        padding: "3px 8px", borderRadius: 4,
                        border: `1px solid ${isEditing ? T.blue : T.border}`,
                        background: isEditing ? `${T.blue}20` : "transparent",
                        color: isEditing ? T.blue : T.text3,
                        fontSize: 10, cursor: "pointer", flexShrink: 0,
                      }}
                    >
                      {isEditing ? "Collapse" : "Edit"}
                    </button>
                    <button
                      onClick={() => isNewRule ? cancelEditing("new") : void deleteRule(ruleCode)}
                      style={{
                        display: "flex", alignItems: "center", justifyContent: "center",
                        width: 24, height: 24, borderRadius: 4,
                        border: `1px solid ${T.border}`, background: "transparent",
                        color: T.text3, cursor: "pointer", flexShrink: 0,
                      }}
                    >
                      <Trash2 size={11} />
                    </button>
                  </div>
                  {isEditing && (
                    <RuleEditor
                      rule={editState}
                      onChange={patch => updateEditingRule(ruleCode, patch)}
                      onSave={() => void saveRule(ruleCode)}
                      onCancel={() => cancelEditing(ruleCode)}
                      categoryTrackers={categoryTrackers}
                      competitorTrackers={competitorTrackers}
                    />
                  )}
                </div>
              )
            })
          )}
        </div>
      )}

      {/* Filters */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap", alignItems: "center" }}>
        <Filter size={13} style={{ color: T.text3 }} />

        {/* Category dropdown */}
        <TrackerDropdown
          label="Category"
          options={activeCategoryOptions}
          selectedCode={filterTrackerType === "CATEGORY" ? selectedTrackerCode : ""}
          onSelect={selectCategory}
        />

        {/* Competitor dropdown */}
        <TrackerDropdown
          label="Competitor"
          options={activeCompetitorOptions}
          selectedCode={filterTrackerType === "COMPETITOR" ? selectedTrackerCode : ""}
          onSelect={selectCompetitor}
        />

        <span style={{ color: T.border2, margin: "0 4px" }}>|</span>

        {/* Severity filter */}
        <div style={{ display: "flex", gap: 4 }}>
          {SEVERITIES.map(sev => {
            const active = filterSeverity === sev
            const sevColor = sev === "HIGH" ? T.red : sev === "MEDIUM" ? T.amber : T.text2
            return (
              <button key={sev} onClick={() => setFilterSeverity(active ? "" : sev)}
                style={{ padding: "5px 10px", borderRadius: 6, border: `1px solid ${active ? sevColor : T.border}`, background: active ? T.bg4 : T.bg2, color: active ? sevColor : T.text2, fontSize: 11, fontWeight: 600, cursor: "pointer", transition: "all .15s" }}>
                {sev}
              </button>
            )
          })}
        </div>

        <span style={{ color: T.border2, margin: "0 4px" }}>|</span>

        {/* Date range filter */}
        <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
          {(["all", "today", "7d", "30d", "custom"] as DatePreset[]).map(p => (
            <button key={p} onClick={() => setDatePreset(p)}
              style={{ padding: "5px 10px", borderRadius: 6, border: `1px solid ${datePreset === p ? T.blue : T.border}`, background: datePreset === p ? T.bg4 : T.bg2, color: datePreset === p ? T.blue : T.text2, fontSize: 11, fontWeight: 600, cursor: "pointer", transition: "all .15s" }}>
              {p === "all" ? "All time" : p === "today" ? "Today" : p === "7d" ? "Last 7d" : p === "30d" ? "Last 30d" : "Custom"}
            </button>
          ))}
          {datePreset === "custom" && (
            <>
              <input type="date" value={customFrom} onChange={e => setCustomFrom(e.target.value)}
                style={{ padding: "4px 8px", borderRadius: 6, border: `1px solid ${T.border}`, background: T.bg2, color: T.text0, fontSize: 11, fontFamily: T.mono, cursor: "pointer" }} />
              <span style={{ color: T.text3, fontSize: 11 }}>-&gt;</span>
              <input type="date" value={customTo} onChange={e => setCustomTo(e.target.value)}
                style={{ padding: "4px 8px", borderRadius: 6, border: `1px solid ${T.border}`, background: T.bg2, color: T.text0, fontSize: 11, fontFamily: T.mono, cursor: "pointer" }} />
            </>
          )}
        </div>

        <span style={{ color: T.border2, margin: "0 4px" }}>|</span>

        {/* Event type filter */}
        <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
          {EVENT_TYPES.map(et => {
            const meta = AlertTypeMeta(et)
            const active = filterType === et
            return (
              <button key={et} onClick={() => setFilterType(active ? "" : et)}
                style={{ display: "flex", alignItems: "center", gap: 4, padding: "5px 8px", borderRadius: 6, border: `1px solid ${active ? meta.color : T.border}`, background: active ? T.bg4 : T.bg2, cursor: "pointer", transition: "all .15s" }}>
                <span style={{ color: meta.color, display: "flex" }}>{meta.icon}</span>
                <span style={{ fontSize: 10, color: active ? meta.color : T.text2, fontFamily: T.mono }}>{meta.label}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/*  Events list */}
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {!loading && error && events.length === 0 && (
          <div style={{ textAlign: "center", padding: 24, color: T.red, fontSize: 12 }}>{error}</div>
        )}
        {loading && <div style={{ textAlign: "center", padding: 40, color: T.text3, fontSize: 13 }}>Loading events...</div>}
        {!loading && events.length === 0 && (
          <div style={{ textAlign: "center", padding: "40px 0", color: T.text3 }}>
            <Filter size={32} style={{ margin: "0 auto 12px", opacity: 0.25 }} />
            <div style={{ fontSize: 13, fontWeight: 600, color: T.text2, marginBottom: 4 }}>
              {filterType || filterSeverity || datePreset !== "all" ? "No events match this filter" : "No events yet"}
            </div>
            <div style={{ fontSize: 11, color: T.text3 }}>
              {filterType || filterSeverity || datePreset !== "all"
                ? "Try adjusting or clearing the filters above."
                : "Events appear here once your trackers start running."}
            </div>
          </div>
        )}
        {!loading && events.map(ev => {
          const meta = AlertTypeMeta(ev.event_type)
          const imageUrl = ev.payload.current?.main_image_url || ev.payload.previous?.main_image_url
            || productImages.get(`${ev.marketplace}:${ev.asin}`)
          return (
            <div key={ev.event_code}
              style={{ background: T.bg2, border: `1px solid ${T.border}`, borderLeft: `3px solid ${meta.color}`, borderRadius: 8, padding: "12px 16px", display: "flex", alignItems: "center", gap: 14, transition: "all .15s" }}
              className="row-hover">
              <div style={{ width: 40, height: 40, borderRadius: 8, background: T.bg3, border: `1px solid ${T.border}`, overflow: "hidden", display: "flex", alignItems: "center", justifyContent: "center", color: meta.color, flexShrink: 0 }}>
                {imageUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={imageUrl} alt={ev.asin} style={{ width: "100%", height: "100%", objectFit: "cover" }} onError={e => { (e.target as HTMLImageElement).style.display = "none" }} />
                ) : (
                  meta.icon
                )}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 3, flexWrap: "wrap" }}>
                  <Badge type={meta.badgeType} text={meta.label} />
                  <Badge type={ev.severity === "HIGH" ? "exit" : ev.severity === "MEDIUM" ? "top10" : "info"} text={ev.severity} />
                  <span style={{ fontSize: 9, fontFamily: T.mono, color: T.text3, padding: "1px 5px", background: T.bg4, borderRadius: 3 }}>
                    {ev.tracker_type}
                  </span>
                </div>
                <div style={{ fontSize: 13, color: T.text0, fontWeight: 500 }}>{ev.title}</div>
                <div style={{ fontSize: 12, color: T.text2, marginTop: 2 }}>{ev.summary}</div>
              </div>
              <div style={{ textAlign: "right", flexShrink: 0 }}>
                <div style={{ fontSize: 10, fontFamily: T.mono, color: T.text3 }}>{new Date(ev.event_time).toLocaleString()}</div>
                <div style={{ fontSize: 10, fontFamily: T.mono, color: T.amber, marginTop: 2 }}>{ev.asin}</div>
                <div style={{ fontSize: 9, fontFamily: T.mono, color: T.text3, marginTop: 2 }}>{ev.tracker_code}</div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Pagination  */}
      {total > 20 && (
        <div style={{ display: "flex", justifyContent: "center", gap: 8, marginTop: 16 }}>
          <button className="btn-ghost" disabled={page <= 1} onClick={() => void loadEvents(page - 1)}>
            <ChevronLeft size={14} /> Prev
          </button>
          <span style={{ fontSize: 11, color: T.text3, fontFamily: T.mono, padding: "6px 10px" }}>
            Page {page} of {Math.ceil(total / 20)}
          </span>
          <button className="btn-ghost" disabled={page >= Math.ceil(total / 20)} onClick={() => void loadEvents(page + 1)}>
            Next <ChevronRight size={14} />
          </button>
        </div>
      )}
    </div>
  )
}
