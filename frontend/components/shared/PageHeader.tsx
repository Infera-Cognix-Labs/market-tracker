import { T } from "./DesignTokens"

export const PageHeader = ({ title, sub, actions }: { title: string; sub?: string; actions?: React.ReactNode }) => (
  <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 24 }}>
    <div>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: T.text0, letterSpacing: "-.02em" }}>{title}</h1>
      {sub && <p style={{ fontSize: 13, color: T.text2, marginTop: 3 }}>{sub}</p>}
    </div>
    {actions && <div style={{ display: "flex", gap: 8, alignItems: "center" }}>{actions}</div>}
  </div>
)
