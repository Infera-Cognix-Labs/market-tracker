import { Plus } from "lucide-react"
import { T } from "./DesignTokens"

interface EmptyStateProps {
  icon: React.ReactNode
  title: string
  message?: string | null
  actionLabel?: string
  onAction?: () => void
}

export const EmptyState = ({ icon, title, message, actionLabel, onAction }: EmptyStateProps) => (
  <div style={{ textAlign: "center", padding: "80px 24px", color: T.text3 }}>
    <div style={{ marginBottom: 16 }}>{icon}</div>
    <div style={{ fontSize: 15, fontWeight: 600, color: T.text1, marginBottom: 6 }}>{title}</div>
    {message && <div style={{ fontSize: 12, color: T.text3, marginBottom: 24 }}>{message}</div>}
    {actionLabel && onAction && (
      <button className="btn-primary" onClick={onAction} style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12 }}>
        <Plus size={14} /> {actionLabel}
      </button>
    )}
  </div>
)
