import { AlertCircle } from "lucide-react"
import { T } from "./DesignTokens"

export const ErrorBanner = ({ message }: { message: string }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "9px 12px", borderRadius: 8, background: `${T.red}18`, border: `1px solid ${T.red}40`, marginBottom: 14 }}>
    <AlertCircle size={13} style={{ color: T.red, flexShrink: 0 }} />
    <span style={{ fontSize: 12, color: T.red }}>{message}</span>
  </div>
)
