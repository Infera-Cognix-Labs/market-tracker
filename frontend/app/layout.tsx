import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "BSR Tracker",
  description: "Amazon Best Seller Rank Tracker",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body style={{ margin: 0, padding: 0 }}>{children}</body>
    </html>
  )
}