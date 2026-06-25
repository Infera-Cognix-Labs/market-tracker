import { TrendingUp, TrendingDown, ArrowUpCircle, ArrowDownCircle, CornerRightUp, Circle, Sparkles } from "lucide-react"
import { T } from "./DesignTokens"

interface KpiFilterBarProps {
  summary: {
    asin_count: number
    new_entrants: number
    returning: number
    exits: number
    enter_top10: number
    exit_top10: number
    up: number
    down: number
    new: number
    stable: number
  }
  activeFilter: string
  onFilterChange: (filter: string) => void
}

export const KpiFilterBar = ({ summary, activeFilter, onFilterChange }: KpiFilterBarProps) => {
  const items = [
    { key: "ALL", label: "Total ASINs", v: summary.asin_count, color: T.text0, icon: <TrendingUp size={14} /> },
    { key: "UP", label: "UP", v: summary.up, color: T.green, icon: <ArrowUpCircle size={14} /> },
    { key: "DOWN", label: "DOWN", v: summary.down, color: T.red, icon: <ArrowDownCircle size={14} /> },
    { key: "NEW", label: "NEW", v: summary.new, color: T.green, icon: <Sparkles size={14} /> },
    { key: "STABLE", label: "STABLE", v: summary.stable, color: T.text3, icon: <Circle size={14} /> },
    { key: "NEW_ENTRANTS", label: "New Entrants", v: summary.new_entrants, color: T.green, icon: <ArrowUpCircle size={14} /> },
    { key: "RETURNING", label: "Returning", v: summary.returning, color: T.blue, icon: <CornerRightUp size={14} /> },
    { key: "EXITS", label: "Exits", v: summary.exits, color: T.red, icon: <ArrowDownCircle size={14} /> },
    { key: "ENTER_TOP10", label: "Enter Top 10", v: summary.enter_top10, color: T.amber, icon: <TrendingUp size={14} /> },
    { key: "EXIT_TOP10", label: "Exit Top 10", v: summary.exit_top10, color: T.red, icon: <TrendingDown size={14} /> },
  ]

  return (
    <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
      {items.map(s => (
        <button key={s.label} type="button" className="card" onClick={() => onFilterChange(s.key)}
          style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 14px", cursor: "pointer", transition: "all .15s", border: `1px solid ${activeFilter === s.key ? s.color : T.border}`, background: activeFilter === s.key ? T.bg3 : T.bg2, flex: "1 1 150px", minWidth: 142 }}>
          <div style={{ width: 30, height: 30, borderRadius: 7, background: `${s.color}18`, display: "flex", alignItems: "center", justifyContent: "center", color: s.color, flexShrink: 0 }}>
            {s.icon}
          </div>
          <div>
            <span style={{ fontSize: 22, fontWeight: 700, fontFamily: T.mono, color: s.color }}>{s.v}</span>
            <div style={{ fontSize: 10, color: T.text2 }}>{s.label}</div>
          </div>
        </button>
      ))}
    </div>
  )
}
