import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'APRIS - AI Repository Analysis',
  description: 'Autonomous Public Repository Intelligence System',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
