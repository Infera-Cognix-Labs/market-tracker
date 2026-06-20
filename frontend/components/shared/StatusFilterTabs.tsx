import { T, statusColor } from "./DesignTokens"

interface StatusFilterTabsProps {
  trackers: Array<{ status?: string }>
  value: string
  onChange: (status: string) => void
}

export const StatusFilterTabs = ({ trackers, value, onChange }: StatusFilterTabsProps) => (
  <div style={{ display: "flex", gap: 8, marginBottom: 12, alignItems: "center", flexWrap: "wrap" }}>
    {(["ACTIVE", "PAUSED", "ARCHIVED"] as const).map(s => {
      const sc = statusColor(s)
      const count = trackers.filter(t => (t.status ?? "ACTIVE") === s).length
      if (count === 0) return null
      return (
        <button key={s} onClick={() => onChange(s)}
          style={{ padding: "5px 12px", borderRadius: 7, border: `1px solid ${value === s ? sc : T.border}`, background: value === s ? T.bg3 : "transparent", color: value === s ? sc : T.text2, fontSize: 12, cursor: "pointer", display: "flex", alignItems: "center", gap: 4, transition: "all .15s", fontFamily: T.sans }}>
          {s} <span style={{ opacity: .7 }}>({count})</span>
        </button>
      )
    })}
  </div>
)
