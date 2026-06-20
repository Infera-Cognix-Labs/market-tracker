import { Zap } from "lucide-react"
import { T } from "./DesignTokens"

interface NoSnapshotPlaceholderProps {
  triggering: boolean
  onTrigger: () => void
}

export const NoSnapshotPlaceholder = ({ triggering, onTrigger }: NoSnapshotPlaceholderProps) => (
  <div style={{ textAlign: "center", padding: "48px 0", color: T.text3, fontSize: 13 }}>
    <div style={{ fontSize: 32, marginBottom: 12 }}>🔍</div>
    <div style={{ fontWeight: 600, color: T.text2, marginBottom: 6 }}>No snapshot yet</div>
    <div style={{ fontSize: 12, marginBottom: 16 }}>This tracker hasn&apos;t run yet.</div>
    <button type="button" disabled={triggering} onClick={onTrigger}
      style={{ padding: "8px 20px", borderRadius: 8, border: `1px solid ${T.blue}`, background: "transparent", color: T.blue, fontSize: 12, cursor: triggering ? "not-allowed" : "pointer", display: "inline-flex", alignItems: "center", gap: 6, transition: "all .15s", fontFamily: T.sans }}>
      <Zap size={14} /> {triggering ? "Triggering..." : "Trigger Now"}
    </button>
  </div>
)
