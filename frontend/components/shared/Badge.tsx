import { T } from "./DesignTokens"

export const Badge = ({ type, text }: { type: string; text: string }) => {
  const map: Record<string, string> = { 
    new: "tag-new", 
    return: "tag-ret", 
    exit: "tag-exit", 
    top10: "tag-top10", 
    price: "tag-price", 
    stock: "tag-stock", 
    listing: "tag-listing", 
    info: "tag-info" 
  }
  return <span className={`badge ${map[type] || "tag-info"}`}>{text}</span>
}
