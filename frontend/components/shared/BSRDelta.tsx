import { ArrowUpRight, ArrowDownRight } from "lucide-react"
import { T } from "./DesignTokens"

export const BSRDelta = ({ cur, prev }: { cur: number; prev: number }) => {
  const d = cur - prev
  if (d === 0) return <span style={{ color: T.text3, fontFamily: T.mono, fontSize: 11 }}>—</span>
  if (d < 0) return <span style={{ color: T.green, fontFamily: T.mono, fontSize: 11, display: "flex", alignItems: "center", gap: 2 }}><ArrowUpRight size={10} />{Math.abs(d).toLocaleString()}</span>
  return <span style={{ color: T.red, fontFamily: T.mono, fontSize: 11, display: "flex", alignItems: "center", gap: 2 }}><ArrowDownRight size={10} />{d.toLocaleString()}</span>
}
