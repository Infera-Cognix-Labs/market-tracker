import { ArrowUpRight, ArrowDownRight } from "lucide-react"
import { T } from "./DesignTokens"
import { Badge } from "./Badge"

export const RankChange = ({ v }: { v: string | null }) => {
  if (!v) return <span style={{ color: T.text3, fontFamily: T.mono, fontSize: 12 }}>—</span>
  if (v === "NEW") return <Badge type="new" text="NEW" />
  const n = parseInt(v)
  if (n > 0) return <span style={{ color: T.green, fontFamily: T.mono, fontSize: 12, display: "flex", alignItems: "center", gap: 2 }}><ArrowUpRight size={11} />+{n}</span>
  if (n < 0) return <span style={{ color: T.red, fontFamily: T.mono, fontSize: 12, display: "flex", alignItems: "center", gap: 2 }}><ArrowDownRight size={11} />{n}</span>
  return <span style={{ color: T.text3, fontFamily: T.mono, fontSize: 12 }}>—</span>
}
