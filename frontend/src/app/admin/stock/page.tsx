'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import {
  listStocks,
  listSources,
  createSource,
  deleteSource,
  createStock,
  incrementStock,
  decrementStock,
} from '@/services/stocks'
import { listBooks } from '@/services/books'
import type { BookRead, SourceStock, Stock } from '@/types/api'

export default function AdminStockPage() {
  const [books, setBooks] = useState<BookRead[]>([])
  const [stocks, setStocks] = useState<Stock[]>([])
  const [sources, setSources] = useState<SourceStock[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busyKey, setBusyKey] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  const [newSourceLibelle, setNewSourceLibelle] = useState('')
  const [newSourceType, setNewSourceType] = useState('ADMIN')

  const [addStockBookId, setAddStockBookId] = useState<Record<number, string>>({})
  const [addStockQty, setAddStockQty] = useState<Record<number, string>>({})

  async function load() {
    try {
      const [b, s, src] = await Promise.all([listBooks(), listStocks(), listSources()])
      setBooks(b)
      setStocks(s)
      setSources(src)
    } catch (e) {
      setError((e as Error).message || 'Erreur de chargement')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const sourceLabel = (id: number) => sources.find((s) => s.id_source_stock === id)?.libelle ?? `Source #${id}`

  async function onIncrement(stock: Stock) {
    setBusyKey(`inc-${stock.id_stock}`)
    setError(null)
    try {
      const updated = await incrementStock(stock.id_stock, 1)
      setStocks((list) => list.map((x) => (x.id_stock === updated.id_stock ? updated : x)))
    } catch (e) {
      setError((e as Error).message || 'Action impossible')
    } finally {
      setBusyKey(null)
    }
  }

  async function onDecrement(stock: Stock) {
    setBusyKey(`dec-${stock.id_stock}`)
    setError(null)
    try {
      const updated = await decrementStock(stock.id_stock, 1)
      setStocks((list) => list.map((x) => (x.id_stock === updated.id_stock ? updated : x)))
    } catch (e) {
      setError((e as Error).message || 'Action impossible')
    } finally {
      setBusyKey(null)
    }
  }

  async function onCreateSource(e: { preventDefault(): void }) {
    e.preventDefault()
    if (!newSourceLibelle.trim()) return
    setError(null)
    try {
      await createSource({ libelle: newSourceLibelle.trim(), type_source: newSourceType.trim() || 'ADMIN' })
      setNewSourceLibelle('')
      await load()
    } catch (e) {
      setError((e as Error).message || 'Création impossible')
    }
  }

  async function onDeleteSource(id: number) {
    if (!confirm('Supprimer cette source de stock ? (impossible si du stock y est encore rattaché)')) return
    setError(null)
    try {
      await deleteSource(id)
      await load()
    } catch (e) {
      setError((e as Error).message || 'Suppression impossible (stock encore rattaché ?)')
    }
  }

  async function onAddStock(book: BookRead) {
    const sourceIdStr = addStockBookId[book.id_article]
    const qtyStr = addStockQty[book.id_article] || '1'
    if (!sourceIdStr) return
    setBusyKey(`add-${book.id_article}`)
    setError(null)
    try {
      await createStock({
        id_article: book.id_article,
        id_source_stock: Number(sourceIdStr),
        quantite_disponible: Number(qtyStr) || 0,
      })
      setAddStockBookId((m) => ({ ...m, [book.id_article]: '' }))
      setAddStockQty((m) => ({ ...m, [book.id_article]: '' }))
      await load()
    } catch (e) {
      setError((e as Error).message || 'Ajout impossible (peut-être déjà une entrée pour ce livre+source ?)')
    } finally {
      setBusyKey(null)
    }
  }

  const filteredBooks = books.filter((b) => {
    if (!search.trim()) return true
    const q = search.trim().toLowerCase()
    return `${b.titre} ${b.auteur ?? ''} ${b.isbn}`.toLowerCase().includes(q)
  })

  if (loading) return <div className="muted">Chargement…</div>

  return (
    <div style={{ display: 'grid', gap: 24 }}>
      <h1 style={{ margin: 0 }}>Stock</h1>
      {error ? <div className="banner-error">{error}</div> : null}

      <section style={{ display: 'grid', gap: 10 }}>
        <h2 style={{ margin: 0, fontSize: '1.1rem' }}>Sources d&apos;approvisionnement</h2>
        <form onSubmit={onCreateSource} style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <input className="input" style={{ flex: '1 1 200px' }} placeholder="Libellé (ex: Magasin, Don, Entrepôt…)" value={newSourceLibelle} onChange={(e) => setNewSourceLibelle(e.target.value)} required />
          <input className="input" style={{ flex: '1 1 140px' }} placeholder="Type (ex: ADMIN, DON)" value={newSourceType} onChange={(e) => setNewSourceType(e.target.value)} />
          <button className="btn btnPrimary" type="submit">Ajouter</button>
        </form>
        <div className="card" style={{ padding: 8 }}>
          {sources.length === 0 ? (
            <div className="muted" style={{ padding: 8 }}>Aucune source</div>
          ) : sources.map((s, i) => (
            <div key={s.id_source_stock} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 8px', borderBottom: i < sources.length - 1 ? '1px solid var(--color-border)' : 'none' }}>
              <span style={{ fontWeight: 700, flex: 1 }}>{s.libelle}</span>
              <span className="muted" style={{ fontSize: 12 }}>{s.type_source}</span>
              <button className="btn" style={{ fontSize: 12, padding: '3px 10px', color: '#dc2626' }} onClick={() => onDeleteSource(s.id_source_stock)}>Supprimer</button>
            </div>
          ))}
        </div>
      </section>

      <section style={{ display: 'grid', gap: 10 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <h2 style={{ margin: 0, fontSize: '1.1rem' }}>Quantités par livre</h2>
          <input className="input" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Rechercher un livre…" style={{ maxWidth: 280 }} />
        </div>
        <div className="card" style={{ padding: '0 4px' }}>
          {filteredBooks.length === 0 ? (
            <div className="muted" style={{ padding: 16 }}>Aucun livre</div>
          ) : filteredBooks.map((b, i) => {
            const rows = stocks.filter((s) => s.id_article === b.id_article)
            return (
              <div key={b.id_article} style={{ padding: '10px 8px', borderBottom: i < filteredBooks.length - 1 ? '1px solid var(--color-border)' : 'none', display: 'grid', gap: 6 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
                  <Link href={`/admin/books/${b.id_article}`} style={{ fontWeight: 700, textDecoration: 'none', color: 'var(--color-text)' }}>{b.titre}</Link>
                  <span className="muted" style={{ fontSize: 11 }}>ISBN {b.isbn}</span>
                </div>
                {rows.length === 0 ? (
                  <div className="muted" style={{ fontSize: 12 }}>Aucun stock enregistré</div>
                ) : rows.map((s) => (
                  <div key={s.id_stock} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13 }}>
                    <span style={{ minWidth: 100 }}>{sourceLabel(s.id_source_stock)}</span>
                    <span className="muted">disponible : <strong style={{ color: 'var(--color-text)' }}>{s.quantite_disponible}</strong></span>
                    <span className="muted">réservé : {s.quantite_reservee ?? 0}</span>
                    <button className="btn" style={{ fontSize: 12, padding: '2px 8px' }} disabled={busyKey === `dec-${s.id_stock}` || s.quantite_disponible <= 0} onClick={() => onDecrement(s)}>−1</button>
                    <button className="btn" style={{ fontSize: 12, padding: '2px 8px' }} disabled={busyKey === `inc-${s.id_stock}`} onClick={() => onIncrement(s)}>+1</button>
                  </div>
                ))}
                {sources.length > 0 ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 2 }}>
                    <select
                      className="input"
                      style={{ fontSize: 12, padding: '3px 6px' }}
                      value={addStockBookId[b.id_article] || ''}
                      onChange={(e) => setAddStockBookId((m) => ({ ...m, [b.id_article]: e.target.value }))}
                    >
                      <option value="">+ nouvelle source de stock…</option>
                      {sources
                        .filter((s) => !rows.some((r) => r.id_source_stock === s.id_source_stock))
                        .map((s) => (
                          <option key={s.id_source_stock} value={s.id_source_stock}>{s.libelle}</option>
                        ))}
                    </select>
                    <input
                      className="input"
                      type="number"
                      min={0}
                      style={{ width: 70, fontSize: 12, padding: '3px 6px' }}
                      placeholder="qté"
                      value={addStockQty[b.id_article] || ''}
                      onChange={(e) => setAddStockQty((m) => ({ ...m, [b.id_article]: e.target.value }))}
                    />
                    <button
                      className="btn"
                      style={{ fontSize: 12, padding: '3px 10px' }}
                      disabled={!addStockBookId[b.id_article] || busyKey === `add-${b.id_article}`}
                      onClick={() => onAddStock(b)}
                    >
                      Ajouter
                    </button>
                  </div>
                ) : null}
              </div>
            )
          })}
        </div>
      </section>
    </div>
  )
}
