import { T } from "./DesignTokens"

interface PriceDisplayProps {
  current: number
  original?: number | null
  currency?: string | null
  marketplace?: string
}

const getSymbol = (currency?: string | null, marketplace?: string): string => {
  if (currency === "EUR" || marketplace?.includes("_de") || marketplace?.includes("_fr") || marketplace?.includes("_it") || marketplace?.includes("_es")) return "€"
  if (currency === "GBP" || marketplace?.includes("_uk")) return "£"
  return "$"
}

export const PriceDisplay = ({ current, original, currency, marketplace }: PriceDisplayProps) => {
  if (!current || current <= 0) return <span style={{ color: T.text3 }}>—</span>
  const sym = getSymbol(currency, marketplace)
  return (
    <>
      {sym}{current.toFixed(2)}
      {original != null && original > current && (
        <span style={{ fontSize: 10, color: T.text3, textDecoration: "line-through", marginLeft: 4 }}>
          {sym}{original.toFixed(2)}
        </span>
      )}
    </>
  )
}
