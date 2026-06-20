import { T } from "./DesignTokens"

interface ThumbnailImageProps {
  src?: string | null
  alt: string
  size?: number
  fallback?: React.ReactNode
}

export const ThumbnailImage = ({ src, alt, size = 36, fallback }: ThumbnailImageProps) => (
  <div style={{ width: size, height: size, borderRadius: size > 40 ? 8 : 6, background: T.bg3, border: `1px solid ${T.border}`, overflow: "hidden", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
    {src ? (
      // eslint-disable-next-line @next/next/no-img-element
      <img src={src} alt={alt} style={{ width: "100%", height: "100%", objectFit: "cover" }} onError={e => { (e.target as HTMLImageElement).style.display = "none" }} />
    ) : fallback ?? <span style={{ fontSize: 10, color: T.text3, fontFamily: T.mono }}>N/A</span>}
  </div>
)
