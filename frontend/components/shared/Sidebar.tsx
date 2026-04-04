import { Activity, BarChart2, Package, Bell, Briefcase, FileText, Search } from "lucide-react"
import { T } from "./DesignTokens"

const NAV = [
  { id: "dashboard", label: "Dashboard", icon: <Activity size={16} /> },
  { id: "categories", label: "Categories", icon: <BarChart2 size={16} /> },
  { id: "competitors", label: "Competitors", icon: <Package size={16} /> },
  { id: "search", label: "Node Search", icon: <Search size={16} /> },
  { id: "events", label: "Events", icon: <Bell size={16} /> },
  { id: "jobs", label: "Jobs", icon: <Briefcase size={16} /> },
  { id: "reports", label: "Reports", icon: <FileText size={16} /> },
]

export const Sidebar = ({ page, setPage }: { page: string; setPage: (page: string) => void }) => (
  <div style={{ width: 210, flexShrink: 0, background: T.bg1, borderRight: `1px solid ${T.border}`, display: "flex", flexDirection: "column", height: "100vh", position: "sticky", top: 0 }}>
    {/* Logo */}
    <div style={{ padding: "18px 18px 14px", borderBottom: `1px solid ${T.border}` }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{ width: 28, height: 28, borderRadius: 7, background: `linear-gradient(135deg, ${T.amber} 0%, ${T.amberD} 100%)`, display: "flex", alignItems: "center", justifyContent: "center" }}>
          📈
        </div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: T.text0, letterSpacing: "-.01em" }}>Market Tracker</div>
          <div style={{ fontSize: 10, color: T.text3, fontFamily: T.mono }}>v1.0</div>
        </div>
      </div>
    </div>
    {/* Nav */}
    <nav style={{ padding: "10px 10px", flex: 1 }}>
      {NAV.map(n => {
        const active = page === n.id
        return (
          <button key={n.id} onClick={() => setPage(n.id)}
            style={{ width: "100%", display: "flex", alignItems: "center", gap: 10, padding: "9px 10px", borderRadius: 8, border: "none", cursor: "pointer", marginBottom: 2, background: active ? T.bg4 : "transparent", color: active ? T.text0 : T.text2, fontFamily: T.sans, fontSize: 13, fontWeight: active ? 500 : 400, transition: "all .15s", position: "relative", textAlign: "left" }}>
            <span style={{ color: active ? T.amber : T.text3 }}>{n.icon}</span>
            {n.label}
          </button>
        )
      })}
    </nav>
    {/* Status footer */}
    <div style={{ padding: "12px 14px", borderTop: `1px solid ${T.border}` }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
        <span className="dot-live" />
        <span style={{ fontSize: 11, color: T.text2 }}>System online</span>
      </div>
      <div style={{ fontSize: 10, fontFamily: T.mono, color: T.text3 }}>API: mock mode</div>
    </div>
  </div>
)
