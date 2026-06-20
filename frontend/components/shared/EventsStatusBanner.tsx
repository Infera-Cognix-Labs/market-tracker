import { T } from "./DesignTokens"

interface EventsStatusBannerProps {
  loading: boolean
  error: string | null
  onRetry?: () => void
}

export const EventsStatusBanner = ({ loading, error, onRetry }: EventsStatusBannerProps) => (
  <>
    {loading && (
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 14px", marginBottom: 8, borderRadius: 8, background: `${T.blue}12`, border: `1px solid ${T.blue}30`, fontSize: 12, color: T.blue }}>
        <span className="dot-live" style={{ background: T.blue, animation: "pulse 1.5s infinite" }} />
        Loading events...
      </div>
    )}
    {error && !loading && (
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 14px", marginBottom: 8, borderRadius: 8, background: `${T.red}12`, border: `1px solid ${T.red}30`, fontSize: 12, color: T.red }}>
        {error}
        {onRetry && (
          <button onClick={onRetry} style={{ marginLeft: "auto", padding: "3px 10px", borderRadius: 6, border: `1px solid ${T.red}40`, background: "transparent", color: T.red, fontSize: 11, cursor: "pointer" }}>
            Retry
          </button>
        )}
      </div>
    )}
  </>
)
