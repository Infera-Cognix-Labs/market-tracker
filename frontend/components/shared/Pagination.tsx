import { ChevronLeft, ChevronRight } from "lucide-react"
import { T } from "./DesignTokens"

interface PaginationProps {
  page: number
  totalPages: number
  onPageChange: (page: number) => void
}

export const Pagination = ({ page, totalPages, onPageChange }: PaginationProps) => {
  if (totalPages <= 1) return null
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, justifyContent: "center", padding: "8px 0" }}>
      <button disabled={page <= 1} onClick={() => onPageChange(page - 1)}
        style={{ padding: "4px 8px", borderRadius: 6, border: `1px solid ${T.border}`, background: T.bg3, color: page <= 1 ? T.text3 : T.text1, cursor: page <= 1 ? "not-allowed" : "pointer", display: "flex", alignItems: "center", fontSize: 12 }}>
        <ChevronLeft size={14} /> Prev
      </button>
      <span style={{ fontSize: 11, color: T.text3, fontFamily: T.mono }}>{page} / {totalPages}</span>
      <button disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}
        style={{ padding: "4px 8px", borderRadius: 6, border: `1px solid ${T.border}`, background: T.bg3, color: page >= totalPages ? T.text3 : T.text1, cursor: page >= totalPages ? "not-allowed" : "pointer", display: "flex", alignItems: "center", fontSize: 12 }}>
        Next <ChevronRight size={14} />
      </button>
    </div>
  )
}
