import { T } from "./DesignTokens"
import type { TrackerStatus } from "./types"

export const StatusToggle = ({ value, onChange }: { value: TrackerStatus; onChange: (v: TrackerStatus) => void }) => (
  <div style={{ display: "flex", gap: 8 }}>
    {(["ACTIVE", "PAUSED", "ARCHIVED"] as TrackerStatus[]).map(s => (
      <button key={s} type="button" onClick={() => onChange(s)}
        style={{ flex: 1, padding: "9px 12px", borderRadius: 8, border: `1px solid ${value === s ? (s === "ACTIVE" ? T.green : s === "PAUSED" ? T.amber : T.red) : T.border}`, background: value === s ? T.bg4 : T.bg3, color: value === s ? (s === "ACTIVE" ? T.green : s === "PAUSED" ? T.amber : T.red) : T.text2, fontSize: 12, cursor: "pointer", transition: "all .15s", fontFamily: T.sans }}>
        {s}
      </button>
    ))}
  </div>
)
