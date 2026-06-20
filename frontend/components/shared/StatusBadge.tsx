import { T } from "./DesignTokens"

export const StatusBadge = ({ status }: { status?: string }) => {
  const isActive = status === "ACTIVE"
  const isPaused = status === "PAUSED"
  const label = isActive ? "Active" : isPaused ? "Paused" : "Error"
  const bg = isActive ? "#0F2A1A" : "#2A100F"
  const color = isActive ? T.green : T.red
  const border = isActive ? T.greenD : T.redD

  return (
    <span style={{ fontSize: 10, fontWeight: 600, padding: "2px 8px", borderRadius: 4, background: bg, color, border: `1px solid ${border}`, fontFamily: T.mono }}>
      {label}
    </span>
  )
}
