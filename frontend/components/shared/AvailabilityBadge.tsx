export const AvailabilityBadge = ({ status }: { status: string }) => {
  const isInStock = status === "IN_STOCK"
  const label = isInStock ? "In Stock" : status === "OUT_OF_STOCK" ? "OOS" : status
  const type = isInStock ? "listing" : "stock"
  const map: Record<string, string> = { listing: "tag-listing", stock: "tag-stock" }
  return <span className={`badge ${map[type]}`}>{label}</span>
}
