'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import type { BookRead, Stock } from '@/types/api'
import { listBooks, deleteBook } from '@/services/books'
import { listStocks } from '@/services/stocks'
import { ApiError } from '@/services/api'

export default function AdminBooksPage() {
  const [books, setBooks] = useState<BookRead[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [stockMap, setStockMap] = useState<Record<number, number>>({})

  useEffect(() => {
    let mounted = true
    setLoading(true)
    listBooks()
      .then((b) => {
        if (!mounted) return
        setBooks(b)
      })
      .finally(() => {
        // fetch stocks
        listStocks()
          .then((s: Stock[]) => {
            if (!mounted) return
            const map: Record<number, number> = {}
            for (const st of s || []) {
              const avail = (st.quantite_disponible || 0) - (st.quantite_reservee || 0)
              map[st.id_article] = (map[st.id_article] || 0) + avail
            }
            setStockMap(map)
          })
          .catch(() => {})
      })
      .catch((e: unknown) => {
        if (!mounted) return
        setError(e instanceof ApiError ? e.message : 'Erreur de chargement')
      })
      .finally(() => {
        if (!mounted) return
        setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [])

  return (
    <div style={{ display: 'grid', gap: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <Link className="btn btnPrimary" href="/admin/books/new">
            + Ajouter
          </Link>
          <h1 style={{ margin: 0 }}>Livres</h1>
        </div>
        <div />
      </div>

      {loading ? <div className="muted">Chargement…</div> : null}
      {error ? <div className="muted">{error}</div> : null}

      <div className="card" style={{ padding: 12, display: 'grid', gap: 10 }}>
        {books.map((b) => (
          <div
            key={b.id_article}
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              gap: 10,
              borderBottom: '1px solid var(--color-border)',
              paddingBottom: 10,
              alignItems: 'center',
            }}
          >
            <div style={{ display: 'grid' }}>
              <div style={{ fontWeight: 800 }}>{b.titre}</div>
              <div className="muted" style={{ fontSize: 13 }}>
                ISBN {b.isbn} · id {b.id_article} · stock {stockMap[b.id_article] || 0}
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <Link className="btn" href={`/admin/books/${b.id_article}`}>
                Modifier
              </Link>
              <button
                className="btn"
                onClick={async () => {
                  if (!confirm('Supprimer ce livre ?')) return
                  try {
                    await deleteBook(b.id_article)
                    setBooks((prev) => prev.filter((x) => x.id_article !== b.id_article))
                  } catch (e) {
                    alert('Erreur lors de la suppression')
                  }
                }}
              >
                Supprimer
              </button>
            </div>
          </div>
        ))}
        {!books.length && !loading ? <div className="muted">Aucun livre.</div> : null}
      </div>
    </div>
  )
}
