import { Trash2 } from "lucide-react"
import { T } from "./DesignTokens"

export const DeleteButton = ({ onClick, label = "Delete" }: { onClick: () => void; label?: string }) => (
  <button type="button" onClick={onClick}
    style={{ padding: "9px 14px", borderRadius: 8, border: `1px solid ${T.red}40`, background: "transparent", color: T.red, fontSize: 12, cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 4, fontFamily: T.sans }}>
    <Trash2 size={12} /> {label}
  </button>
)
