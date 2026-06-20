"use client"

import { AlertTriangle, X } from "lucide-react"
import { T } from "./DesignTokens"

interface ConfirmDialogProps {
  open: boolean
  title: string
  message: React.ReactNode
  confirmLabel?: string
  onConfirm: () => void
  onCancel: () => void
  loading?: boolean
}

export const ConfirmDialog = ({ open, title, message, confirmLabel = "Delete", onConfirm, onCancel, loading }: ConfirmDialogProps) => {
  if (!open) return null

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)", zIndex: 200, display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
      <div style={{ background: T.bg2, border: `1px solid ${T.border}`, borderRadius: 12, width: "100%", maxWidth: 400, padding: "24px 28px", position: "relative" }}>
        <button onClick={onCancel} style={{ position: "absolute", top: 16, right: 16, background: "none", border: "none", cursor: "pointer", color: T.text3, display: "flex" }}>
          <X size={16} />
        </button>

        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: `${T.red}18`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <AlertTriangle size={20} style={{ color: T.red }} />
          </div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: T.text0 }}>{title}</div>
          </div>
        </div>

        <p style={{ fontSize: 13, color: T.text2, lineHeight: 1.5, marginBottom: 24 }}>
          {message}
        </p>

        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <button onClick={onCancel} disabled={loading}
            style={{ padding: "9px 16px", borderRadius: 8, border: `1px solid ${T.border}`, background: "none", color: T.text1, fontSize: 13, fontFamily: T.sans, cursor: loading ? "not-allowed" : "pointer" }}>
            Cancel
          </button>
          <button onClick={onConfirm} disabled={loading}
            style={{ padding: "9px 16px", borderRadius: 8, border: "none", background: loading ? T.bg4 : T.red, color: "#fff", fontSize: 13, fontWeight: 600, fontFamily: T.sans, cursor: loading ? "not-allowed" : "pointer", display: "flex", alignItems: "center", gap: 6, opacity: loading ? 0.6 : 1 }}>
            {loading ? "Deleting…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
