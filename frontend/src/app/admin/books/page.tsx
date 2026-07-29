'use client'

import Link from 'next/link'
import Image from 'next/image'
import { useEffect, useState } from 'react'
import type { BookRead } from '@/types/api'
import { listBooks, deleteBook } from '@/services/books'
import { getAvailabilityMap } from '@/services/stocks'
import { ApiError } from '@/services/api'

export default function AdminBooksPage() {
  const [books, setBooks] = useState<BookRead[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [stockMap, setStockMap] = useState<Record<number, number>>({})
  const [search, setSearch] = useState('')
  const [deletingId, setDeletingId] = useState<number | null>(null)

  useEffect(() => {
    let mounted = true
    Promise.all([listBooks(), getAvailabilityMap().catch(() => ({}) as Record<number, number>)]).then(([b, map]) => {
      if (!mounted) return
      setBooks(b)
      setStockMap(map)
    }).catch((e: unknown) => {
      if (!mounted) return
      setError(e instanceof ApiError ? e.message : 'Erreur de chargement')
    }).finally(() => { if (mounted) setLoading(false) })
    return () => { mounted = false }
  }, [])

  const filtered = books.filter((b) => {
    const q = search.trim().toLowerCase()
    if (!q) return true
    return `${b.titre} ${b.auteur ?? ''} ${b.isbn}`.toLowerCase().includes(q)
  })

  async function onDelete(id: number) {
    if (!confirm('Supprimer ce livre ?')) return
    setDeletingId(id)
    try {
      await deleteBook(id)
      setBooks((prev) => prev.filter((x) => x.id_article !== id))
    } catch {
      alert('Erreur lors de la suppression')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div style={{ display: 'grid', gap: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
        <h1 style={{ margin: 0 }}>Livres <span className="muted" style={{ fontWeight: 400, fontSize: '0.9rem' }}>({books.length})</span></h1>
        <Link className="btn btnPrimary" href="/admin/books/new">+ Ajouter un livre</Link>
      </div>

      {loading ? <div className="muted">Chargement…</div> : null}
      {error ? <div className="banner-error">{error}</div> : null}

      <input
        className="input"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Rechercher par titre, auteur ou ISBN…"
      />

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {filtered.length === 0 && !loading ? (
          <div className="muted" style={{ padding: 16 }}>Aucun livre trouvé.</div>
        ) : (
          filtered.map((b) => {
            const stock = stockMap[b.id_article] ?? 0
            return (
              <div
                key={b.id_article}
                style={{ display: 'flex', gap: 12, padding: '10px 14px', borderBottom: '1px solid var(--color-border)', alignItems: 'center' }}
              >
                <div style={{ width: 40, height: 56, borderRadius: 4, overflow: 'hidden', background: '#f3f4f6', flexShrink: 0, position: 'relative' }}>
                  {b.image_link ? (
                    <Image src={b.image_link} alt={b.titre} fill style={{ objectFit: 'cover' }} sizes="40px" unoptimized />
                  ) : (
                    <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18 }}>📖</div>
                  )}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 700, fontSize: 14, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{b.titre}</div>
                  <div className="muted" style={{ fontSize: 12, display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 2 }}>
                    <span>{b.auteur || '—'}</span>
                    {b.etat_libelle ? <span>· {b.etat_libelle}</span> : null}
                    {b.categorie_libelles?.length ? <span>· {b.categorie_libelles[0]}</span> : null}
                    <span>· {b.prix_chf.toFixed(2)} CHF</span>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                  <span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 999, background: stock > 0 ? '#d1fae5' : '#fee2e2', color: stock > 0 ? '#065f46' : '#dc2626', fontWeight: 700 }}>
                    Stock: {stock}
                  </span>
                  {!b.actif ? <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 999, background: '#f3f4f6', color: '#6b7280', fontWeight: 600 }}>Inactif</span> : null}
                  <Link className="btn" style={{ fontSize: 12, padding: '4px 10px' }} href={`/admin/books/${b.id_article}`}>Modifier</Link>
                  <button
                    className="btn"
                    style={{ fontSize: 12, padding: '4px 10px', color: '#dc2626' }}
                    disabled={deletingId === b.id_article}
                    onClick={() => onDelete(b.id_article)}
                  >
                    {deletingId === b.id_article ? '…' : 'Supprimer'}
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
