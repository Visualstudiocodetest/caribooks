import Link from 'next/link'

export function Footer() {
  return (
    <footer style={{ borderTop: '1px solid var(--color-border)', padding: '18px 0' }}>
      <div
        className="container"
        style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: 8 }}
      >
        <div className="muted" suppressHydrationWarning>
          © {new Date().getFullYear()} Caribooks — Devise: CHF · Livraison: Suisse
        </div>
        <div style={{ display: 'flex', gap: 16 }}>
          <Link href="/mentions-legales" className="muted" style={{ fontSize: '0.85rem' }}>
            Mentions légales
          </Link>
          <Link href="/conditions-utilisation" className="muted" style={{ fontSize: '0.85rem' }}>
            Conditions d&apos;utilisation
          </Link>
          <Link href="/confidentialite" className="muted" style={{ fontSize: '0.85rem' }}>
            Confidentialité
          </Link>
        </div>
      </div>
    </footer>
  )
}
