import { X } from "lucide-react"
import { T } from "./DesignTokens"

export const ModalOverlay = ({ children }: { children: React.ReactNode }) => (
  <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)", zIndex: 100, overflowY: "auto" }}>
    <div style={{ minHeight: "100%", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
      {children}
    </div>
  </div>
)

export const ModalCard = ({ children }: { children: React.ReactNode }) => (
  <div style={{ background: T.bg2, border: `1px solid ${T.border}`, borderRadius: 12, width: "100%", maxWidth: 480, padding: "24px 28px", position: "relative" }}>
    {children}
  </div>
)

export const ModalHeader = ({ title, onClose }: { title: string; onClose: () => void }) => (
  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
    <span style={{ fontSize: 16, fontWeight: 700, color: T.text0 }}>{title}</span>
    <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: T.text3, display: "flex" }}>
      <X size={18} />
    </button>
  </div>
)

export const ModalFooter = ({
  onCancel,
  onSubmitLabel,
  submitting,
  submitIcon,
}: {
  onCancel: () => void
  onSubmitLabel: string
  submitting?: boolean
  submitIcon?: React.ReactNode
}) => (
  <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 20 }}>
    <button type="button" onClick={onCancel} className="btn-ghost">Cancel</button>
    <button type="submit" disabled={submitting} className="btn-primary" style={{ display: "flex", alignItems: "center", gap: 6 }}>
      {submitIcon} {submitting ? "Saving…" : onSubmitLabel}
    </button>
  </div>
)
