import { T } from "./DesignTokens"

export const InfoBanner = ({ message }: { message: string }) => (
  <div style={{ background: `${T.blue}15`, border: `1px solid ${T.blue}40`, borderRadius: 8, padding: "12px 14px", marginBottom: 16, color: T.blue, fontSize: 12 }}>
    {message}
  </div>
)
