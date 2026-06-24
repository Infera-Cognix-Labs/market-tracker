import { ExternalLink } from "lucide-react"
import { T } from "./DesignTokens"
import { Badge } from "./Badge"
import { StatusBadge } from "./StatusBadge"

interface TrackerInfoCardProps {
  name: string
  titleHref?: string | null
  marketplace?: string
  status?: string
  meta?: string
  statsRight?: React.ReactNode
  children?: React.ReactNode
}

export const TrackerInfoCard = ({ name, titleHref, marketplace, status, meta, statsRight, children }: TrackerInfoCardProps) => (
  <div className="card-info">
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 2 }}>
          {titleHref ? (
            <a href={titleHref} target="_blank" rel="noopener noreferrer"
              style={{ fontSize: 16, fontWeight: 700, letterSpacing: "-.01em", color: T.text0, lineHeight: 1.2, textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 5 }}>
              {name}<ExternalLink size={12} />
            </a>
          ) : (
            <span style={{ fontSize: 16, fontWeight: 700, letterSpacing: "-.01em", color: T.text0, lineHeight: 1.2 }}>{name}</span>
          )}
          {marketplace && <Badge type="top10" text={marketplace.toUpperCase()} />}
          <StatusBadge status={status} />
        </div>
        {meta && <div style={{ fontSize: 12, color: T.text2, marginTop: 6 }}>{meta}</div>}
        {children}
      </div>
      {statsRight && (
        <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
          {statsRight}
        </div>
      )}
    </div>
  </div>
)

export const TrackerStat = ({ label, value }: { label: string; value: React.ReactNode }) => (
  <div style={{ display: "grid", gridTemplateColumns: "90px 1fr", gap: 4, fontSize: 11, color: T.text3, fontFamily: T.mono, padding: "2px 0" }}>
    <span>{label}</span>
    <span style={{ color: T.text1, textAlign: "right" }}>{value}</span>
  </div>
)
