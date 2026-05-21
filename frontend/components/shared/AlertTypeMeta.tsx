import { T } from "./DesignTokens"
import { Zap, Star, TrendingDown, RefreshCw, Eye, Package, FileText, Image as ImageIcon, Grid3x3, ShoppingCart, Tag, AlertTriangle } from "lucide-react"

/** Maps API EventType enum values to display metadata */
export const AlertTypeMeta = (type: string) => ({
  NEW_ENTRANT_TOP50: { label: "New Entrant", color: T.green, badgeType: "new", icon: <Zap size={12} /> },
  RETURNING_TOP50: { label: "Returning", color: "#90EE90", badgeType: "return", icon: <RefreshCw size={12} /> },
  EXIT_TOP50: { label: "Exit Top 50", color: T.red, badgeType: "exit", icon: <TrendingDown size={12} /> },
  ENTER_TOP10: { label: "Enter Top 10", color: T.amber, badgeType: "top10", icon: <Star size={12} /> },
  EXIT_TOP10: { label: "Exit Top 10", color: T.red, badgeType: "exit", icon: <TrendingDown size={12} /> },
  PRICE_CHANGED: { label: "Price Changed", color: T.blue, badgeType: "price", icon: <TrendingDown size={12} /> },
  PROMOTION_CHANGED: { label: "Promotion Changed", color: T.amber, badgeType: "price", icon: <Tag size={12} /> },
  TITLE_CHANGED: { label: "Title Changed", color: T.purple, badgeType: "listing", icon: <FileText size={12} /> },
  MAIN_IMAGE_CHANGED: { label: "Image Changed", color: T.purple, badgeType: "listing", icon: <ImageIcon size={12} /> },
  VARIATIONS_ADDED: { label: "Variations Added", color: T.teal, badgeType: "listing", icon: <Grid3x3 size={12} /> },
  CONTENT_CHANGED: { label: "Content Changed", color: T.teal, badgeType: "listing", icon: <Eye size={12} /> },
  AVAILABILITY_CHANGED: { label: "Availability Changed", color: T.purple, badgeType: "stock", icon: <Package size={12} /> },
  BUY_BOX_CHANGED: { label: "Buy Box Changed", color: T.blue, badgeType: "price", icon: <ShoppingCart size={12} /> },
} as Record<string, { label: string; color: string; badgeType: string; icon: React.ReactNode }>)[type] || {
  label: type,
  color: T.text2,
  badgeType: "info",
  icon: <AlertTriangle size={12} />,
}
