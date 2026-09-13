import Link from 'next/link'
import { listBooks } from '@/services/books'
import { getAvailabilityMap } from '@/services/stocks'
import { listCatalog } from '@/services/catalog'
import { CatalogClient, type EtatItem } from '@/components/catalog/CatalogClient'

export const dynamic = 'force-dynamic'

export default async function HomePage() {
  const books = await listBooks().catch(() => [])
  // One batched availability request instead of fetching the whole /stock/ list
  // and reducing it here (the map is now computed server-side in a single query).
  const availability = await getAvailabilityMap().catch(() => ({}) as Record<number, number>)
  // Reference lists fetched server-side alongside books/availability, instead of
  // a client-side waterfall after CatalogClient mounts.
  const etatList = await listCatalog<EtatItem>('etat-usures').catch(() => [])

  // Show only books with remaining stock. availability keys are numbers server-side
  // but arrive as string keys once JSON-serialized — index defensively.
  const availAt = (id: number) => availability[id] ?? (availability as Record<string, number>)[String(id)] ?? 0
  const available = books.filter((b) => availAt(b.id_article) > 0)

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

      {/* Full catalog: search, filters, sort */}
      <CatalogClient
        books={available}
        availability={availability}
        etatList={etatList}
      />
    </div>
  )
}
