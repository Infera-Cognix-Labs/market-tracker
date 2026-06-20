import { T } from "./DesignTokens"
import type { DealInfo, Event, CategorySnapshotProduct } from "./types"

// ── Constants ──────────────────────────────────────────────────────────────────

export const MARKETPLACES = [
  { value: "amazon_us", label: "🇺🇸 amazon_us" },
  { value: "amazon_de", label: "🇩🇪 amazon_de" },
  { value: "amazon_uk", label: "🇬🇧 amazon_uk" },
  { value: "amazon_fr", label: "🇫🇷 amazon_fr" },
  { value: "amazon_it", label: "🇮🇹 amazon_it" },
  { value: "amazon_es", label: "🇪🇸 amazon_es" },
  { value: "amazon_ca", label: "🇨🇦 amazon_ca" },
  { value: "amazon_jp", label: "🇯🇵 amazon_jp" },
]

export const HOURS = Array.from({ length: 24 }, (_, i) => ({ value: i, label: `${String(i).padStart(2, "0")}:00 UTC` }))

export const FILTER_TO_EVENT: Record<string, string> = {
  NEW_ENTRANTS: "NEW_ENTRANT_TOP50",
  RETURNING: "RETURNING_TOP50",
  EXITS: "EXIT_TOP50",
  ENTER_TOP10: "ENTER_TOP10",
  EXIT_TOP10: "EXIT_TOP10",
}

// ── Formatting Helpers ─────────────────────────────────────────────────────────

export const formatMoney = (value: number, currency?: string | null): string => {
  const symbol = currency === "EUR" ? "€" : currency === "GBP" ? "£" : "$"
  return `${symbol}${value.toFixed(2)}`
}

// ── Parsing Helpers ────────────────────────────────────────────────────────────

export function parseBestsellerUrl(input: string): string | null {
  const trimmed = input.trim()
  if (!trimmed.startsWith("http")) return null
  try {
    const url = new URL(trimmed)
    if (url.hostname.includes("amazon.") && (trimmed.includes("/zgbs/") || trimmed.includes("Best-Sellers") || trimmed.includes("best-sellers"))) {
      return trimmed
    }
    return null
  } catch {
    return null
  }
}

export const extractBrandName = (url: string): string => {
  if (!url) return url
  try {
    let match = url.match(/\/stores\/([^/]+)\//)
    if (match?.[1]) return match[1]
    match = url.match(/\/([^/]+)\/b\//)
    if (match?.[1]) return match[1]
    return url
  } catch {
    return url
  }
}

export const parseCouponItems = (couponText?: string | null): string[] => {
  if (!couponText) return []
  return couponText
    .split(/\r?\n|\s*\|\s*|\s*;\s*/)
    .map(item => item.trim())
    .filter(Boolean)
}

export const parseDealItems = (dealInfo?: DealInfo | null): string[] => {
  if (!dealInfo) return []
  const items: string[] = []

  if (dealInfo.deal_badge) items.push(dealInfo.deal_badge)

  const typeAndState = [dealInfo.deal_type, dealInfo.deal_state].filter(Boolean).join(" • ")
  if (typeAndState) items.push(typeAndState)

  if (dealInfo.deal_price != null) {
    items.push(`Deal: ${formatMoney(dealInfo.deal_price, dealInfo.currency)}`)
  }
  if (dealInfo.list_price != null) {
    items.push(`List: ${formatMoney(dealInfo.list_price, dealInfo.currency)}`)
  }
  if (dealInfo.savings_percentage != null || dealInfo.savings_amount != null) {
    const pct = dealInfo.savings_percentage != null ? `${dealInfo.savings_percentage}%` : null
    const amt = dealInfo.savings_amount != null ? formatMoney(dealInfo.savings_amount, dealInfo.currency) : null
    items.push(`Savings: ${[pct, amt].filter(Boolean).join(" • ")}`)
  }

  return items.length > 0 ? items : ["Deal available"]
}

// ── Product/Event Helpers ──────────────────────────────────────────────────────

export const rankTrendMeta = (product: CategorySnapshotProduct) => {
  if (product.rank_trend === "NEW") return { color: T.green, label: "New" }
  if (product.rank_trend === "UP") return { color: T.green, label: `+${product.rank_delta}` }
  if (product.rank_trend === "DOWN") return { color: T.red, label: `${product.rank_delta}` }
  if (product.rank_trend === "STABLE") return { color: T.text3, label: "0" }
  return { color: T.text3, label: "—" }
}

export const getEventImageUrl = (event: Event): string | null => {
  return event.payload.current?.main_image_url || event.payload.previous?.main_image_url || null
}

export const eventToProduct = (event: Event): CategorySnapshotProduct => {
  const prev = event.payload.previous
  const prevRank = event.payload.previous_rank ?? null
  const curRank = event.payload.current_rank ?? null
  const rank = prevRank ?? curRank ?? 0
  const currency = prev?.price_current != null ? (event.marketplace === "amazon_us" ? "USD" : event.marketplace === "amazon_uk" ? "GBP" : "EUR") : "USD"

  let rankDelta: number | null = null
  let rankTrend: CategorySnapshotProduct["rank_trend"] = null
  if (prevRank != null && curRank != null) {
    rankDelta = curRank - prevRank
    if (rankDelta > 0) rankTrend = "DOWN"
    else if (rankDelta < 0) rankTrend = "UP"
    else rankTrend = "STABLE"
  }

  return {
    asin: event.asin,
    rank_position: rank,
    previous_rank_position: prevRank,
    rank_delta: rankDelta,
    rank_trend: rankTrend,
    title: prev?.title || event.title || "",
    brand: extractBrandName(prev?.brand || ""),
    product_url: prev?.price_current != null ? `https://www.${event.marketplace.replace("amazon_", "amazon.")}/dp/${event.asin}` : "",
    price_current: prev?.price_current ?? 0,
    price_original: prev?.price_original ?? null,
    currency,
    rating_value: prev?.rating_value ?? 0,
    review_count: prev?.review_count ?? 0,
    image_url: prev?.main_image_url || "",
    availability_status: prev?.availability_status ?? "UNKNOWN",
    buy_box_status: prev?.buy_box_status ?? "UNKNOWN",
    coupon_text: prev?.coupon_text ?? null,
    deal_info: prev?.deal_info ?? null,
  }
}

// ── Search Helpers ─────────────────────────────────────────────────────────────

export const matchesProductSearch = (search: string, product: CategorySnapshotProduct): boolean => {
  if (!search) return true
  const q = search.toLowerCase()
  return (
    product.title.toLowerCase().includes(q) ||
    product.asin.toLowerCase().includes(q) ||
    product.brand.toLowerCase().includes(q)
  )
}

export const matchesEventSearch = (search: string, event: Event, includeSummary = true): boolean => {
  if (!search) return true
  const q = search.toLowerCase()
  return (
    event.title.toLowerCase().includes(q) ||
    event.asin.toLowerCase().includes(q) ||
    (includeSummary && event.summary.toLowerCase().includes(q))
  )
}
