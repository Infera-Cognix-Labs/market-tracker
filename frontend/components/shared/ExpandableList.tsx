import { T } from "./DesignTokens"

interface ExpandableListProps {
  items: string[]
  label: string
  isOpen: boolean
  onToggle: () => void
  color?: string
  colorBorder?: string
  colorBg?: string
  fontSize?: number
  padding?: string
  borderRadius?: number
  minWidth?: number
}

export const ExpandableList = ({
  items,
  label,
  isOpen,
  onToggle,
  color = T.blue,
  colorBorder,
  colorBg,
  fontSize = 10,
  padding = "4px 8px",
  borderRadius = 6,
  minWidth = 160,
}: ExpandableListProps) => (
  <div style={{ minWidth }}>
    <button
      type="button"
      onClick={onToggle}
      style={{
        padding,
        borderRadius,
        border: `1px solid ${colorBorder ?? color}`,
        background: colorBg ?? `${color}16`,
        color,
        fontSize,
        fontFamily: T.mono,
        fontWeight: 600,
        cursor: "pointer",
      }}
    >
      {isOpen ? "Hide" : "View"} {label}
    </button>
    {isOpen && (
      <div style={{ marginTop: borderRadius! < 6 ? 4 : 6, padding: borderRadius! < 6 ? "4px 6px" : "6px 8px", background: T.bg3, border: `1px solid ${T.border}`, borderRadius, color: T.text1, fontSize: borderRadius! < 6 ? 10 : 11, lineHeight: 1.4 }}>
        {items.map((item, idx) => (
          <div key={`${item}-${idx}`} style={{ marginBottom: idx < items.length - 1 ? (borderRadius! < 6 ? 3 : 4) : 0 }}>• {item}</div>
        ))}
      </div>
    )}
  </div>
)
