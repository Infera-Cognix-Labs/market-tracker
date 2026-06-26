"use client"

import { AlertCircle, Edit2, ExternalLink, Layers3, Plus, Settings, Trash2, X } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { Badge } from "../shared/Badge"
import { ConfirmDialog } from "../shared/ConfirmDialog"
import { T } from "../shared/DesignTokens"
import { Dropdown } from "../shared/Dropdown"
import { ErrorBanner } from "../shared/ErrorBanner"
import { PageHeader } from "../shared/PageHeader"
import { PriceDisplay } from "../shared/PriceDisplay"
import { SearchInput } from "../shared/SearchInput"
import { StatusFilterTabs } from "../shared/StatusFilterTabs"
import { ThumbnailImage } from "../shared/ThumbnailImage"
import { TrackerInfoCard, TrackerStat } from "../shared/TrackerInfoCard"
import {
  apiCreateKeywordGroup,
  apiDeleteKeywordGroup,
  apiGetLatestKeywordGroupSnapshot,
  apiListKeywordGroups,
  apiListKeywordTrackers,
  apiReplaceTrackedKeywords,
  apiUpdateKeywordGroup,
} from "../shared/api"
import { MARKETPLACES } from "../shared/formatting"
import { handleApiError } from "../shared/hooks"
import type { KeywordGroup, KeywordGroupCreateRequest, KeywordGroupProduct, KeywordGroupSnapshot, KeywordGroupUpdateRequest, KeywordTracker, TrackerStatus, TrackedKeywordInput } from "../shared/types"

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
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)", zIndex: 100, overflowY: "auto" }}>
      <div style={{ minHeight: "100%", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
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
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)", zIndex: 100, overflowY: "auto" }}>
      <div style={{ minHeight: "100%", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
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
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)", zIndex: 100, overflowY: "auto" }}>
      <div style={{ minHeight: "100%", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
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

const rankList = (product: KeywordGroupProduct) => Object.entries(product.keyword_ranks).sort((a, b) => a[1] - b[1])

const KeywordGroupSnapshotTable = ({ snapshot, loading, search, onSearchChange }: { snapshot: KeywordGroupSnapshot | null; loading: boolean; search: string; onSearchChange: (value: string) => void }) => {
  const [selectedProductIdx, setSelectedProductIdx] = useState(0)
  const filteredProducts = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!snapshot) return []
    if (!q) return snapshot.products
    return snapshot.products.filter(p => [p.asin, p.title, p.brand, ...p.keyword_list].some(value => value?.toLowerCase().includes(q)))
  }, [snapshot, search])
  const effectiveIdx = filteredProducts.length === 0 ? 0 : Math.min(selectedProductIdx, filteredProducts.length - 1)
  const selectedProduct = filteredProducts[effectiveIdx]

  const renderTableRows = () => {
    if (!snapshot) return null
    return (
      <div style={{ width: "100%", overflowX: "auto" }}>
        <table style={{ width: "100%", minWidth: 1120, borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: `1px solid ${T.border}` }}>
              {["Coverage", "Avg", "Best", "Worst", "Img", "ASIN", "Title", "Brand", "Price", "Availability", "Keywords"].map(h => <th key={h} className="th">{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {filteredProducts.map(product => (
              <tr key={product.asin} className="row-hover" style={{ borderBottom: `1px solid ${T.border}`, background: product.keyword_count > 1 ? `${T.bg3}50` : "transparent" }}>
                <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 13, color: T.amber, fontWeight: 700 }}>{product.keyword_count}</td>
                <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 12, color: T.text1 }}>#{product.avg_rank.toFixed(1)}</td>
                <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 12, color: T.green }}>#{product.best_rank}</td>
                <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 12, color: T.text2 }}>#{product.worst_rank}</td>
                <td style={{ padding: "6px 10px" }}><ThumbnailImage src={product.image_url ?? ""} alt={product.asin} /></td>
                <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 11 }}>
                  <a href={product.product_url || `https://www.amazon.com/dp/${product.asin}`} target="_blank" rel="noopener noreferrer" style={{ color: T.blue, textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 3 }}>
                    {product.asin}<ExternalLink size={9} />
                  </a>
                </td>
                <td style={{ padding: "9px 10px", fontSize: 12, color: T.text0, maxWidth: 280 }}><div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{product.title}</div></td>
                <td style={{ padding: "9px 10px", fontSize: 11, color: T.text2, maxWidth: 110 }}><div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{product.brand || "-"}</div></td>
                <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 12, color: T.text1, whiteSpace: "nowrap" }}><PriceDisplay current={product.current_price ?? 0} currency={product.currency} marketplace={snapshot.marketplace} /></td>
                <td style={{ padding: "9px 10px" }}><Badge type={product.availability_status === "IN_STOCK" ? "listing" : "stock"} text={product.availability_status === "IN_STOCK" ? "In Stock" : product.availability_status === "OUT_OF_STOCK" ? "OOS" : product.availability_status} /></td>
                <td style={{ padding: "9px 10px", minWidth: 240 }}>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                    {rankList(product).slice(0, 5).map(([keyword, rank]) => (
                      <span key={keyword} title={keyword} style={{ padding: "2px 6px", borderRadius: 5, border: `1px solid ${T.border}`, background: T.bg4, color: T.text2, fontSize: 10, maxWidth: 140, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        #{rank} {keyword}
                      </span>
                    ))}
                    {product.keyword_count > 5 && <span style={{ color: T.text3, fontSize: 10, padding: "2px 0" }}>+{product.keyword_count - 5}</span>}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  const renderDetailLayout = () => {
    if (!snapshot) return null
    return (
      <div className="card" style={{ padding: 14, overflow: "hidden" }}>
        <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: 16 }}>
          <div>
            <div style={{ fontSize: 10, fontWeight: 600, color: T.text3, letterSpacing: ".08em", textTransform: "uppercase", marginBottom: 8, padding: "0 4px" }}>
              {filteredProducts.length} aggregated ASINs
            </div>
            <div style={{ maxHeight: 680, overflowY: "auto", paddingRight: 4 }}>
              {filteredProducts.map((product, i) => (
                <div key={product.asin} className="row-hover" onClick={() => setSelectedProductIdx(i)}
                  style={{ padding: "10px 12px", borderRadius: 8, marginBottom: 4, background: i === effectiveIdx ? T.bg4 : T.bg2, border: `1px solid ${i === effectiveIdx ? T.border2 : T.border}`, cursor: "pointer", transition: "all .15s" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 4 }}>
                    <span style={{ fontSize: 11, fontFamily: T.mono, color: T.text3 }}>{product.asin}</span>
                    <span style={{ fontSize: 11, fontFamily: T.mono, color: T.amber, fontWeight: 700 }}>{product.keyword_count} kw</span>
                  </div>
                  <div style={{ fontSize: 12, color: T.text0, fontWeight: 500, lineHeight: 1.3, marginBottom: 6, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{product.title}</div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr auto", alignItems: "center", gap: 6 }}>
                    <span style={{ fontFamily: T.mono, fontSize: 12, color: T.text1 }}>avg #{product.avg_rank.toFixed(1)}</span>
                    <Badge type={product.availability_status === "IN_STOCK" ? "listing" : "stock"} text={product.availability_status === "IN_STOCK" ? "In Stock" : product.availability_status === "OUT_OF_STOCK" ? "OOS" : product.availability_status} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {selectedProduct && (
            <div key={selectedProduct.asin} className="anim-slide">
              <div className="card" style={{ marginBottom: 12 }}>
                <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
                  <ThumbnailImage src={selectedProduct.image_url ?? ""} alt={selectedProduct.title || selectedProduct.asin} size={52} fallback="IMG" />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 15, fontWeight: 600, color: T.text0, marginBottom: 3 }}>{selectedProduct.title}</div>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 6 }}>
                      <a href={selectedProduct.product_url || `https://www.amazon.com/dp/${selectedProduct.asin}`} target="_blank" rel="noopener noreferrer" style={{ fontSize: 11, fontFamily: T.mono, color: T.blue, textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 3 }}>{selectedProduct.asin}<ExternalLink size={9} /></a>
                      <span style={{ fontSize: 11, color: T.text2 }}>{selectedProduct.brand || "-"}</span>
                      <Badge type={selectedProduct.availability_status === "IN_STOCK" ? "listing" : "stock"} text={selectedProduct.availability_status === "IN_STOCK" ? "In Stock" : selectedProduct.availability_status === "OUT_OF_STOCK" ? "Out of Stock" : selectedProduct.availability_status} />
                    </div>
                    <div style={{ display: "flex", gap: 12, fontSize: 11, color: T.text1, flexWrap: "wrap" }}>
                      <span>Price: <span style={{ fontFamily: T.mono }}><PriceDisplay current={selectedProduct.current_price ?? 0} currency={selectedProduct.currency} marketplace={snapshot.marketplace} /></span></span>
                      <span>Coverage: <span style={{ color: T.amber, fontFamily: T.mono }}>{selectedProduct.keyword_count}/{snapshot.keyword_count}</span></span>
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 20, flexShrink: 0 }}>
                    {[
                      { label: "Avg", v: `#${selectedProduct.avg_rank.toFixed(1)}`, color: T.text0 },
                      { label: "Best", v: `#${selectedProduct.best_rank}`, color: T.green },
                      { label: "Worst", v: `#${selectedProduct.worst_rank}`, color: T.text2 },
                      { label: "Keywords", v: selectedProduct.keyword_count, color: T.amber },
                    ].map(stat => (
                      <div key={stat.label} style={{ textAlign: "center" }}>
                        <div style={{ fontSize: 16, fontWeight: 700, fontFamily: T.mono, color: stat.color }}>{stat.v}</div>
                        <div style={{ fontSize: 10, color: T.text3, marginTop: 2 }}>{stat.label}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="card" style={{ padding: 0, overflow: "hidden" }}>
                <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}`, fontSize: 13, fontWeight: 600, color: T.text1 }}>Keyword Rank Coverage</div>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead><tr style={{ borderBottom: `1px solid ${T.border}` }}>{["Rank", "Keyword"].map(h => <th key={h} className="th">{h}</th>)}</tr></thead>
                  <tbody>
                    {rankList(selectedProduct).map(([keyword, rank]) => (
                      <tr key={keyword} className="row-hover" style={{ borderBottom: `1px solid ${T.border}` }}>
                        <td style={{ padding: "9px 10px", width: 80, fontFamily: T.mono, fontSize: 12, color: rank <= 10 ? T.amber : T.text1, fontWeight: rank <= 10 ? 700 : 500 }}>#{rank}</td>
                        <td style={{ padding: "9px 10px", fontSize: 12, color: T.text0 }}>{keyword}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="card" style={{ padding: 0, overflow: "hidden", marginBottom: 14 }}>
        <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}`, display: "flex", alignItems: "center", gap: 10 }}>
          <SearchInput value={search} onChange={onSearchChange} placeholder="Search ASIN, title, brand, or keyword..." />
          <span style={{ fontSize: 11, color: T.text3, fontFamily: T.mono, marginLeft: "auto" }}>{filteredProducts.length} of {snapshot?.total_unique_asins ?? 0} products</span>
        </div>
        {loading ? (
          <div style={{ textAlign: "center", padding: 40, color: T.text3 }}>Loading group snapshot...</div>
        ) : !snapshot ? (
          <div style={{ textAlign: "center", padding: 46, color: T.text3 }}><AlertCircle size={22} style={{ marginBottom: 8, opacity: 0.5 }} /><br />No aggregated snapshot available for this group.</div>
        ) : filteredProducts.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px 0", color: T.text3, fontSize: 13 }}>No products match your search</div>
        ) : renderTableRows()}
      </div>
      {!loading && snapshot && filteredProducts.length > 0 && renderDetailLayout()}
    </>
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
  const [search, setSearch] = useState("")
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
      <PageHeader title="Keyword Groups" sub="Aggregate products across multiple keyword trackers" actions={<div style={{ display: "flex", gap: 8 }}>{selectedGroup && <button className="btn-ghost" onClick={() => setShowManage(true)} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}><Settings size={14} /> Manage Keywords</button>}{selectedGroup && <button className="btn-ghost" onClick={() => setShowEdit(true)} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}><Edit2 size={14} /> Edit Group</button>}<button className="btn-primary" onClick={() => setShowCreate(true)} style={{ display: "flex", alignItems: "center", gap: 6 }}><Plus size={14} /> New Group</button></div>} />
      {error && <ErrorBanner message={error} />}
      <StatusFilterTabs trackers={selectorGroups} value={statusFilter} onChange={setStatusFilter} />
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        {groups.filter(group => (group.status ?? "ACTIVE") === statusFilter).map(group => {
          const isSelected = group.group_code === selectedCode
          const sc = statusColor(group.status)
          return (
            <button key={group.group_code} onClick={() => { setSnapshotLoading(true); setSearch(""); setSelectedCode(group.group_code) }}
              style={{ padding: "7px 14px", borderRadius: 8, border: `1px solid ${isSelected ? sc : T.border}`, background: isSelected ? T.bg4 : T.bg2, color: isSelected ? sc : T.text1, fontSize: 13, fontFamily: T.sans, cursor: "pointer", transition: "all .15s", display: "flex", alignItems: "center", gap: 6 }}>
              {isSelected && <span className="dot-live" style={{ background: sc, boxShadow: `0 0 0 3px ${sc}30` }} />}
              {group.name}
              <span style={{ fontSize: 10, fontFamily: T.mono, color: T.text3 }}>({group.marketplace})</span>
            </button>
          )
        })}
      </div>
      {selectedGroup && <TrackerInfoCard name={selectedGroup.name} marketplace={selectedGroup.marketplace} status={selectedGroup.status} meta={`${selectedGroup.tracked_keywords.filter(k => k.enabled).length} active keywords - ${selectedGroup.tracked_keywords.length} total`} statsRight={<><TrackerStat label="Unique ASINs" value={selectedGroup.latest_snapshot_summary?.total_unique_asins ?? snapshot?.total_unique_asins ?? "-"} /><TrackerStat label="Snapshots" value={selectedGroup.stats.total_snapshots_covered} /></>}><div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>{selectedGroup.tracked_keywords.slice(0, 8).map(keyword => <span key={keyword.tracker_code} style={{ padding: "3px 7px", borderRadius: 5, border: `1px solid ${keyword.enabled ? T.border2 : T.border}`, background: keyword.enabled ? T.bg4 : T.bg3, color: keyword.enabled ? T.text2 : T.text3, fontSize: 10 }}>{keyword.keyword_snapshot}{!keyword.enabled ? " - off" : ""}</span>)}{selectedGroup.tracked_keywords.length > 8 && <span style={{ color: T.text3, fontSize: 10, padding: "3px 0" }}>+{selectedGroup.tracked_keywords.length - 8}</span>}</div></TrackerInfoCard>}
      {snapshot && <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 10, marginBottom: 16 }}>{[["Unique ASINs", snapshot.total_unique_asins], ["Keywords", snapshot.keyword_count], ["Overlap", snapshot.products.filter(p => p.keyword_count > 1).length], ["Captured", new Date(snapshot.captured_at).toLocaleDateString()]].map(([label, value]) => <div key={label} className="card" style={{ padding: "12px 14px" }}><div style={{ fontSize: 11, color: T.text3, marginBottom: 4 }}>{label}</div><div style={{ fontSize: 18, color: T.text0, fontWeight: 700, fontFamily: T.mono }}>{value}</div></div>)}</div>}
      <KeywordGroupSnapshotTable snapshot={snapshot} loading={snapshotLoading} search={search} onSearchChange={setSearch} />
    </div>
  )
}










