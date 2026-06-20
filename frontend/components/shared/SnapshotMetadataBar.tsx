import { T } from "./DesignTokens"

interface SnapshotMetadataBarProps {
  snapshotDate: string
  capturedAt: string
  sourceRefs?: React.ReactNode
}

export const SnapshotMetadataBar = ({ snapshotDate, capturedAt, sourceRefs }: SnapshotMetadataBarProps) => (
  <div style={{ display: "flex", gap: 12, marginBottom: 8, fontSize: 11, color: T.text3, fontFamily: T.mono, flexWrap: "wrap", alignItems: "center" }}>
    <span>Snapshot: {snapshotDate}</span>
    <span>·</span>
    <span>Captured: {new Date(capturedAt).toLocaleString()}</span>
    {sourceRefs}
  </div>
)
