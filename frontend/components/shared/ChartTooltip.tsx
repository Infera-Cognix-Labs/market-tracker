import { T } from "./DesignTokens"

interface ChartTooltipProps {
  active?: boolean;
  payload?: Array<{ value?: number }>;
  label?: string;
}

export const ChartTooltip = ({ active, payload, label }: ChartTooltipProps) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: T.bg4, border: `1px solid ${T.border2}`, borderRadius: 8, padding: "8px 12px", fontFamily: T.mono, fontSize: 12 }}>
      <div style={{ color: T.text2, marginBottom: 4 }}>{label}</div>
      <div style={{ color: T.amber, fontWeight: 600 }}>#{payload[0]?.value?.toLocaleString()}</div>
    </div>
  )
}
