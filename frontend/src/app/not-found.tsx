import Link from 'next/link'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Page introuvable',
}

// Rendered for any unmatched URL and whenever a route calls notFound()
// (e.g. /books/[id] for an unknown book). Served with a 404 status.
export default function NotFound() {
  return (
    <div className="content-center">
      <div className="card cardPadding" style={{ display: 'grid', gap: 12, justifyItems: 'start' }}>
        <h1 style={{ margin: 0 }}>Page introuvable</h1>
        <p className="muted" style={{ margin: 0 }}>
          La page demandée n&apos;existe pas ou le livre a été retiré du catalogue.
        </p>
        <Link className="btn btnPrimary" href="/">
          Retour au catalogue
        </Link>
      </div>
    </div>
  )
}
