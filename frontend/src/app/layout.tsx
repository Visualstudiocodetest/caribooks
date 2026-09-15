import type { Metadata, Viewport } from 'next'
import './globals.css'
import { Header } from '@/components/layout/Header'
import { Footer } from '@/components/layout/Footer'
import { CookieBanner } from '@/components/ui/CookieBanner'
import { Providers } from './providers'
import type { ReactNode } from 'react'
import { SpeedInsights } from '@vercel/speed-insights/next'
import { Analytics } from '@vercel/analytics/next'

export const metadata: Metadata = {
  // Resolves the relative URLs Next generates for Open Graph / canonical tags.
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL || 'https://caribooks.vercel.app',
  ),
  title: {
    default: 'Caribooks',
    // Pages set only their own title; Next appends the site name.
    template: '%s — Caribooks',
  },
  description: 'Livres de seconde main — Caritas',
  openGraph: {
    siteName: 'Caribooks',
    locale: 'fr_CH',
    type: 'website',
  },
}

// The viewport meta tag goes through the Metadata API rather than a hand-written
// <meta> in <head>: Next already emits `width=device-width, initial-scale=1` by
// default, and a manual tag would sit alongside its generated one.
export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
}

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode
}>) {
  return (
    <html lang="fr">
      <body>
        <Providers>
          <Header />
          <main className="page-main">
            <div className="container">{children}</div>
          </main>
          <Footer />
          <CookieBanner />
        </Providers>
        <SpeedInsights />
        <Analytics />
      </body>
    </html>
  )
}

