import { T } from "./DesignTokens"

export const KPICard = ({ label, value, sub, delta, icon, accent }: { label: string; value: string | number; sub?: string; delta?: number; icon?: React.ReactNode; accent?: string }) => (
  <div className="card" style={{ flex: 1, minWidth: 0 }}>
    <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 12 }}>
      <span style={{ fontSize: 11, fontWeight: 600, color: T.text2, letterSpacing: ".06em", textTransform: "uppercase" }}>{label}</span>
      <span style={{ color: accent || T.text3 }}>{icon}</span>
    </div>
    <div style={{ fontSize: 28, fontWeight: 700, fontFamily: T.mono, color: T.text0, lineHeight: 1 }}>{value}</div>
    {(sub || delta) && (
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 8 }}>
        {delta && <span style={{ fontSize: 11, fontFamily: T.mono, color: delta > 0 ? T.green : T.red, display: "flex", alignItems: "center", gap: 2 }}>{delta > 0 ? "+" : ""}{delta}%</span>}
        {sub && <span style={{ fontSize: 11, color: T.text3 }}>{sub}</span>}
      </div>
    )}
  </div>
)
