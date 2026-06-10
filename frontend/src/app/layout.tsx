import type { Metadata } from 'next'
import './globals.css'
import { Header } from '@/components/layout/Header'
import { Footer } from '@/components/layout/Footer'
import { Providers } from './providers'
import type { ReactNode } from 'react'
import { SpeedInsights } from '@vercel/speed-insights/next'

export const metadata: Metadata = {
  title: 'Caribooks',
  description: 'Livres de seconde main — Caritas',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode
}>) {
  return (
    <html lang="fr">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body>
        <Providers>
          <Header />
          <main className="page-main">
            <div className="container">{children}</div>
          </main>
          <Footer />
        </Providers>
        <SpeedInsights />
      </body>
    </html>
  )
}

