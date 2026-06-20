import { Search } from "lucide-react"
import { T } from "./DesignTokens"

interface SearchInputProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

export const SearchInput = ({ value, onChange, placeholder = "Search..." }: SearchInputProps) => (
  <div style={{ position: "relative", flex: 1, maxWidth: 280 }}>
    <Search size={13} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: T.text3 }} />
    <input className="input" placeholder={placeholder} value={value} onChange={e => onChange(e.target.value)} style={{ paddingLeft: 30 }} />
  </div>
)
