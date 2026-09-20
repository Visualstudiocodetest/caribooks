import Link from 'next/link'
import { listBooks } from '@/services/books'
import { getAvailabilityMap } from '@/services/stocks'
import { listCatalog } from '@/services/catalog'
import { CatalogClient, type EtatItem } from '@/components/catalog/CatalogClient'

export const dynamic = 'force-dynamic'

export default async function HomePage() {
  // These three calls are independent — run them in parallel rather than one
  // after another. Sequential awaits used to triple the round-trip time to
  // the backend, which was long enough on a cold/first request (before this
  // process had a warm connection to the backend) to occasionally let one of
  // them time out — and when it was `getAvailabilityMap`, every book got
  // hidden (see below), which read as "no books on first load, fine after a
  // reload" once the connection was warm.
  const [booksResult, availabilityResult, etatList] = await Promise.all([
    listBooks().catch(() => null),
    getAvailabilityMap().catch(() => null),
    listCatalog<EtatItem>('etat-usures').catch(() => []),
  ])
  const books = booksResult ?? []
  const availability = availabilityResult ?? {}

  // Show only books with remaining stock. availability keys are numbers server-side
  // but arrive as string keys once JSON-serialized — index defensively.
  const availAt = (id: number) => availability[id] ?? (availability as Record<string, number>)[String(id)] ?? 0
  // A failed availability fetch means "unknown", not "zero everywhere" — the
  // old code couldn't tell the two apart, so any hiccup on this one request
  // emptied the whole catalogue instead of just leaving stock badges off.
  const available = availabilityResult ? books.filter((b) => availAt(b.id_article) > 0) : books

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
          <span aria-hidden="true" style={{ fontSize: 36 }}>📚</span>
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
              <span aria-hidden="true" style={{ fontSize: 22 }}>{icon}</span>
              <span style={{ fontSize: 14, fontWeight: 600 }}>{label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Full catalog: search, filters, sort */}
      <CatalogClient
        books={available}
        availability={availability}
        etatList={etatList}
      />
    </div>
  )
}
