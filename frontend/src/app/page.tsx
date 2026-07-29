import Link from 'next/link'
import { listBooks } from '@/services/books'
import { getAvailabilityMap } from '@/services/stocks'
import { BookGrid } from '@/components/books/BookGrid'

export const dynamic = 'force-dynamic'

export default async function HomePage() {
  const books = await listBooks().catch(() => [])
  const recent = books.slice(0, 8)

  // Server-side stock lookup so BookCard can cap "Ajouter au panier" at the
  // real remaining quantity instead of allowing unlimited clicks on a book
  // that's out of stock (the home page, unlike /catalog, doesn't filter
  // unavailable books out of the list at all).
  const availability = await getAvailabilityMap().catch(() => ({}) as Record<number, number>)

  return (
    <div style={{ display: 'grid', gap: 32 }}>
      {/* Hero */}
      <section
        style={{
          background: 'linear-gradient(135deg, var(--color-accent-start), var(--color-accent-end))',
          borderRadius: 'var(--radius)',
          padding: '40px 32px',
          display: 'grid',
          gap: 16,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 36 }}>📚</span>
          <h1 style={{ margin: 0, color: '#1a3a2a', fontSize: 'clamp(1.5rem, 4vw, 2.2rem)' }}>
            Caribooks
          </h1>
        </div>
        <p style={{ margin: 0, color: '#1a3a2a', maxWidth: 520, fontSize: 17, lineHeight: 1.6 }}>
          Livres de seconde main de la recyclerie <strong>Caritas</strong>. Prix en CHF,
          livraison uniquement en Suisse.
        </p>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <Link
            className="btn btnPrimary"
            href="/catalog"
            style={{ background: '#065f46', border: 'none' }}
          >
            Voir le catalogue →
          </Link>
          <Link
            className="btn"
            href="/register"
            style={{ background: 'rgba(255,255,255,0.7)', border: 'none' }}
          >
            Créer un compte
          </Link>
        </div>
      </section>

      {/* Value props */}
      <section>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: 12,
          }}
        >
          {[
            { icon: '🔍', label: 'Recherche par titre, auteur ou ISBN' },
            { icon: '🇨🇭', label: 'Prix en CHF, livraison Suisse uniquement' },
            { icon: '💚', label: 'Profit reversé à Caritas' },
            { icon: '📦', label: 'Livraison PostPac ou retrait en magasin' },
          ].map(({ icon, label }) => (
            <div
              key={label}
              className="card"
              style={{ padding: '14px 16px', display: 'flex', alignItems: 'center', gap: 12 }}
            >
              <span style={{ fontSize: 22 }}>{icon}</span>
              <span style={{ fontSize: 14, fontWeight: 600 }}>{label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Recent books */}
      {recent.length > 0 ? (
        <section style={{ display: 'grid', gap: 14 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'baseline',
              justifyContent: 'space-between',
              gap: 12,
            }}
          >
            <h2 style={{ margin: 0 }}>Dernières arrivées</h2>
            <Link className="muted" href="/catalog" style={{ fontSize: 14 }}>
              Tout voir →
            </Link>
          </div>
          <BookGrid books={recent} availability={availability} />
        </section>
      ) : (
        <section className="card cardPadding" style={{ textAlign: 'center' }}>
          <div className="muted">Le catalogue est en cours de remplissage.</div>
          <Link className="btn btnPrimary" href="/catalog" style={{ marginTop: 10 }}>
            Voir le catalogue
          </Link>
        </section>
      )}
    </div>
  )
}
