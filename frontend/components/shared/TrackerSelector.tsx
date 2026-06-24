import { T, statusColor } from "./DesignTokens"

type TrackerSelectorItem = {
  tracker_code: string
  name: string
  status?: string
  href?: string | null
}

interface TrackerSelectorProps {
  trackers: TrackerSelectorItem[]
  statusFilter: string
  selectedCode: string
  onSelect: (code: string) => void
}

export const TrackerSelector = ({ trackers, statusFilter, selectedCode, onSelect }: TrackerSelectorProps) => (
  <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
    {trackers.filter(t => (t.status ?? "ACTIVE") === statusFilter).map(t => {
      const sc = statusColor(t.status)
      const isSelected = t.tracker_code === selectedCode
      return (
        <div key={t.tracker_code} role="button" tabIndex={0} onClick={() => onSelect(t.tracker_code)}
          onKeyDown={e => { if (e.key === "Enter" || e.key === " ") onSelect(t.tracker_code) }}
          style={{ padding: "7px 14px", borderRadius: 8, border: `1px solid ${isSelected ? sc : T.border}`, background: isSelected ? T.bg3 : "transparent", color: isSelected ? T.text0 : T.text2, fontSize: 13, cursor: "pointer", display: "flex", alignItems: "center", gap: 6, transition: "all .15s", fontFamily: T.sans }}>
          {isSelected && <span className="dot-live" style={{ background: sc, boxShadow: `0 0 0 3px ${sc}30` }} />}
          {t.href ? (
            <a href={t.href} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()}
              style={{ color: T.blue, textDecoration: "none" }}>
              {t.name}
            </a>
          ) : t.name}
        </div>
      )
    })}
  </div>
)
