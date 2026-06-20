"use client"

import { ExternalLink, TrendingDown, TrendingUp } from "lucide-react"
import { Badge } from "../shared/Badge"
import { T } from "../shared/DesignTokens"
import { ExpandableList } from "../shared/ExpandableList"
import { extractBrandName, getEventImageUrl, parseCouponItems, parseDealItems, rankTrendMeta } from "../shared/formatting"
import type { TableRow } from "../shared/hooks"
import { InfoBanner } from "../shared/InfoBanner"
import { NoSnapshotPlaceholder } from "../shared/NoSnapshotPlaceholder"
import { PriceDisplay } from "../shared/PriceDisplay"
import { SearchInput } from "../shared/SearchInput"
import { ThumbnailImage } from "../shared/ThumbnailImage"

interface ProductTableProps {
  search: string
  onSearchChange: (v: string) => void
  allVisibleRows: TableRow[]
  totalFilteredCount: number
  activeKpiFilter: string
  loading: boolean
  openCouponKey: string | null
  openDealKey: string | null
  onOpenCouponKeyChange: (fn: (k: string | null) => string | null) => void
  onOpenDealKeyChange: (fn: (k: string | null) => string | null) => void
  minWidth?: number
  headerExtra?: React.ReactNode
  justAdded: string | null
  triggering: boolean
  onTrigger: () => void
  hasSnapshot?: boolean
  productUrlResolver?: (p: { product_url: string; asin: string }) => string
  brandRenderer?: (brand: string) => React.ReactNode
}

export const ProductTable = ({
  search,
  onSearchChange,
  allVisibleRows,
  totalFilteredCount,
  activeKpiFilter,
  loading,
  openCouponKey,
  openDealKey,
  onOpenCouponKeyChange,
  onOpenDealKeyChange,
  minWidth = 1100,
  headerExtra,
  justAdded,
  triggering,
  onTrigger,
  hasSnapshot = true,
  productUrlResolver,
  brandRenderer,
}: ProductTableProps) => {
  const defaultProductUrl = (p: { product_url: string; asin: string }) => p.product_url || `https://www.amazon.com/dp/${p.asin}`
  const resolveProductUrl = productUrlResolver ?? defaultProductUrl

  const defaultBrandRender = (brand: string) => (
    <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "inline-block", width: "100%" }}>{extractBrandName(brand)}</span>
  )
  const renderBrand = brandRenderer ?? defaultBrandRender

  return (
    <>
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}`, display: "flex", alignItems: "center", gap: 10 }}>
          <SearchInput value={search} onChange={onSearchChange} placeholder="Search ASIN, title, or brand..." />
          {headerExtra}
          <span style={{ fontSize: 11, color: T.text3, fontFamily: T.mono, marginLeft: "auto" }}>
            {allVisibleRows.length} of {totalFilteredCount} {activeKpiFilter === "ALL" ? "products" : "matched rows"}
          </span>
        </div>

        {justAdded && <InfoBanner message="Data will be collected and displayed in a few minutes." />}

        {loading ? (
          <div style={{ textAlign: "center", padding: 40, color: T.text3 }}>Loading snapshot...</div>
        ) : (
          <div style={{ width: "100%", overflowX: "auto" }}>
            <table style={{ width: "100%", minWidth, borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${T.border}` }}>
                  {["#", "Change", "Img", "ASIN", "Title", "Brand", "Price", "Rating", "Reviews", "Availability", "Deal", "Coupon"].map(h => (
                    <th key={h} className="th">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {allVisibleRows.map(row => {
                  if (row.kind === "event") {
                    const event = row.event
                    const imageUrl = getEventImageUrl(event)
                    const rankLabel = event.payload.current_rank ?? event.payload.previous_rank ?? null
                    const prev = event.payload.previous
                    return (
                      <tr key={row.key} className="row-hover" style={{ borderBottom: `1px solid ${T.border}`, background: `${T.bg3}30` }}>
                        <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 13, color: T.text1 }}>
                          {rankLabel != null ? String(rankLabel).padStart(2, "0") : "--"}
                        </td>
                        <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 11, color: T.amber }}>
                          {event.event_type.replaceAll("_", " ")}
                        </td>
                        <td style={{ padding: "6px 10px" }}>
                          <ThumbnailImage src={imageUrl} alt={event.asin} />
                        </td>
                        <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 11, color: T.amber }}>{event.asin}</td>
                        <td style={{ padding: "9px 10px", fontSize: 12, color: T.text0, maxWidth: 240 }}>
                          <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{prev?.title || event.title}</div>
                        </td>
                        <td style={{ padding: "9px 10px", fontSize: 11, color: T.text2, width: 90, maxWidth: 90 }}>
                          {prev?.brand ? (
                            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "inline-block", width: "100%" }}>{extractBrandName(prev.brand)}</span>
                          ) : <span style={{ color: T.text3 }}>—</span>}
                        </td>
                        <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 12, color: T.text1, whiteSpace: "nowrap" }}>
                          <PriceDisplay current={prev?.price_current ?? 0} original={prev?.price_original} marketplace={event.marketplace} />
                        </td>
                        <td style={{ padding: "9px 10px", fontSize: 12, color: T.text3 }}>—</td>
                        <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 11, color: T.text3 }}>—</td>
                        <td style={{ padding: "9px 10px" }}><Badge type="info" text="—" /></td>
                        <td style={{ padding: "9px 10px" }}><Badge type="info" text="—" /></td>
                        <td style={{ padding: "9px 10px", fontSize: 11, color: T.text3 }}>—</td>
                        <td style={{ padding: "9px 10px", fontSize: 11, color: T.text3 }}>—</td>
                      </tr>
                    )
                  }

                  const p = row.product
                  const isExitFilter = activeKpiFilter === "EXITS"
                  return (
                    <tr key={row.key} className="row-hover" style={{ borderBottom: `1px solid ${T.border}`, background: !isExitFilter && p.rank_position <= 10 ? `${T.bg3}50` : "transparent" }}>
                      <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 13, fontWeight: !isExitFilter && p.rank_position <= 10 ? 700 : 400, color: !isExitFilter && p.rank_position <= 10 ? T.amber : T.text1 }}>
                        {isExitFilter ? "—" : String(p.rank_position).padStart(2, "0")}
                      </td>
                      <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 11, whiteSpace: "nowrap" }}>
                        {isExitFilter ? (
                          <span style={{ display: "inline-flex", alignItems: "center", gap: 4, color: T.text3, fontStyle: "italic" }}>
                            Historical
                          </span>
                        ) : (() => {
                          const meta = rankTrendMeta(p)
                          return (
                            <span title={p.comparison_snapshot_date ? `Previous: ${p.previous_rank_position ?? "not ranked"} on ${p.comparison_snapshot_date}` : "No comparison snapshot"}
                              style={{ display: "inline-flex", alignItems: "center", gap: 4, color: meta.color, fontWeight: p.rank_trend && p.rank_trend !== "STABLE" ? 700 : 500 }}>
                              {p.rank_trend === "UP" && <TrendingUp size={12} />}
                              {p.rank_trend === "DOWN" && <TrendingDown size={12} />}
                              {meta.label}
                            </span>
                          )
                        })()}
                      </td>
                      <td style={{ padding: "6px 10px" }}>
                        <ThumbnailImage src={p.image_url} alt={p.asin} />
                      </td>
                      <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 11 }}>
                        <a href={resolveProductUrl(p)} target="_blank" rel="noopener noreferrer" style={{ color: T.blue, textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 3 }}>
                          {p.asin}<ExternalLink size={9} />
                        </a>
                      </td>
                      <td style={{ padding: "9px 10px", fontSize: 12, color: T.text0, maxWidth: 240 }}>
                        <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.title}</div>
                      </td>
                      <td style={{ padding: "9px 10px", fontSize: 11, color: T.text2, width: 90, maxWidth: 90 }}>
                        {p.brand ? renderBrand(p.brand) : <span style={{ color: T.text3 }}>—</span>}
                      </td>
                      <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 12, color: T.text1, whiteSpace: "nowrap" }}>
                        <PriceDisplay current={p.price_current} original={p.price_original} currency={p.currency} />
                      </td>
                      <td style={{ padding: "9px 10px", fontSize: 12, color: T.green }}>
                        {p.rating_value > 0 ? `${p.rating_value}★` : <span style={{ color: T.text3 }}>—</span>}
                      </td>
                      <td style={{ padding: "9px 10px", fontFamily: T.mono, fontSize: 11, color: T.text2 }}>
                        {p.review_count > 0 ? p.review_count.toLocaleString() : <span style={{ color: T.text3 }}>—</span>}
                      </td>
                      <td style={{ padding: "9px 10px" }}>
                        <Badge type={p.availability_status === "IN_STOCK" ? "listing" : "stock"} text={p.availability_status === "IN_STOCK" ? "In Stock" : p.availability_status === "OUT_OF_STOCK" ? "OOS" : p.availability_status} />
                      </td>
                      <td style={{ padding: "9px 10px", fontSize: 11, color: T.blue }}>
                        {(() => {
                          const dealItems = parseDealItems(p.deal_info)
                          if (dealItems.length === 0) return "—"
                          const dealKey = `${p.asin}-${p.rank_position}`
                          return (
                            <ExpandableList
                              items={dealItems}
                              label="Deal"
                              isOpen={openDealKey === dealKey}
                              onToggle={() => onOpenDealKeyChange(prev => prev === dealKey ? null : dealKey)}
                            />
                          )
                        })()}
                      </td>
                      <td style={{ padding: "9px 10px", fontSize: 11, color: T.amber }}>
                        {(() => {
                          const couponItems = parseCouponItems(p.coupon_text)
                          if (couponItems.length === 0) return "—"
                          const couponKey = `${p.asin}-${p.rank_position}`
                          return (
                            <ExpandableList
                              items={couponItems}
                              label={`${couponItems.length} Coupon${couponItems.length > 1 ? "s" : ""}`}
                              isOpen={openCouponKey === couponKey}
                              onToggle={() => onOpenCouponKeyChange(prev => prev === couponKey ? null : couponKey)}
                              color={T.amber}
                              colorBorder={T.amberD}
                              colorBg={`${T.amber}14`}
                            />
                          )
                        })()}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {!loading && !hasSnapshot && <NoSnapshotPlaceholder triggering={triggering} onTrigger={onTrigger} />}
        {!loading && hasSnapshot && allVisibleRows.length === 0 && (
          <div style={{ textAlign: "center", padding: "40px 0", color: T.text3, fontSize: 13 }}>No products match your search</div>
        )}
      </div>
    </>
  )
}
