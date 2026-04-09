import { useEffect } from "react"

export const FontLoader = () => {
  useEffect(() => {
    const link = document.createElement("link")
    link.rel = "stylesheet"
    link.href = "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap"
    document.head.appendChild(link)
  }, [])
  return null
}
