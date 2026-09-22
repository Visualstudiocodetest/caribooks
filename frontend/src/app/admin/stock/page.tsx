'use client'

import { Fragment, useEffect, useState } from 'react'
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
    const sourceIdStr = addStockBookId[book.id_livre]
    const qtyStr = addStockQty[book.id_livre] || '1'
    if (!sourceIdStr) return
    setBusyKey(`add-${book.id_livre}`)
    setError(null)
    try {
      await createStock({
        id_livre: book.id_livre,
        id_source_stock: Number(sourceIdStr),
        quantite_disponible: Number(qtyStr) || 0,
      })
      setAddStockBookId((m) => ({ ...m, [book.id_livre]: '' }))
      setAddStockQty((m) => ({ ...m, [book.id_livre]: '' }))
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

  if (loading) return <div className="muted" role="status" aria-live="polite">Chargement…</div>

  return (
    <div style={{ display: 'grid', gap: 24 }}>
      <h1 style={{ margin: 0 }}>Stock</h1>
      {error ? <div className="banner-error" role="alert">{error}</div> : null}

      <section style={{ display: 'grid', gap: 10 }}>
        <h2 style={{ margin: 0, fontSize: '1.1rem' }}>Sources d&apos;approvisionnement</h2>
        <form onSubmit={onCreateSource} style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <label htmlFor="new-source-libelle" className="sr-only">Libellé de la nouvelle source</label>
          <input id="new-source-libelle" className="input" style={{ flex: '1 1 200px' }} placeholder="Libellé (ex: Magasin, Don, Entrepôt…)" value={newSourceLibelle} onChange={(e) => setNewSourceLibelle(e.target.value)} required />
          <label htmlFor="new-source-type" className="sr-only">Type de la nouvelle source</label>
          <input id="new-source-type" className="input" style={{ flex: '1 1 140px' }} placeholder="Type (ex: ADMIN, DON)" value={newSourceType} onChange={(e) => setNewSourceType(e.target.value)} />
          <button className="btn btnPrimary" type="submit">Ajouter</button>
        </form>
        <div className="card" style={{ padding: 8 }}>
          {sources.length === 0 ? (
            <div className="muted" style={{ padding: 8 }}>Aucune source</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th scope="col" className="sr-only">Libellé</th>
                  <th scope="col" className="sr-only">Type</th>
                  <th scope="col" className="sr-only">Actions</th>
                </tr>
              </thead>
              <tbody>
                {sources.map((s) => (
                  <tr key={s.id_source_stock} style={{ borderBottom: '1px solid var(--color-border)' }}>
                    <td style={{ padding: '8px 8px', fontWeight: 700 }}>{s.libelle}</td>
                    <td className="muted" style={{ padding: '8px 8px', fontSize: 12 }}>{s.type_source}</td>
                    <td style={{ padding: '8px 8px', textAlign: 'right' }}>
                      <button
                        className="btn"
                        style={{ fontSize: 12, padding: '3px 10px', color: '#dc2626' }}
                        onClick={() => onDeleteSource(s.id_source_stock)}
                        aria-label={`Supprimer la source ${s.libelle}`}
                      >
                        Supprimer
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      <section style={{ display: 'grid', gap: 10 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <h2 style={{ margin: 0, fontSize: '1.1rem' }}>Quantités par livre</h2>
          <div>
            <label htmlFor="admin-stock-search" className="sr-only">Rechercher un livre</label>
            <input id="admin-stock-search" className="input" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Rechercher un livre…" style={{ maxWidth: 280 }} />
          </div>
        </div>
        <div className="card" style={{ padding: '0 4px' }}>
          {filteredBooks.length === 0 ? (
            <div className="muted" style={{ padding: 16 }}>Aucun livre</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th scope="col" style={{ textAlign: 'left', padding: '8px', fontSize: 12 }}>Livre</th>
                  <th scope="col" style={{ textAlign: 'left', padding: '8px', fontSize: 12 }}>Source</th>
                  <th scope="col" style={{ textAlign: 'left', padding: '8px', fontSize: 12 }}>Disponible</th>
                  <th scope="col" style={{ textAlign: 'left', padding: '8px', fontSize: 12 }}>Réservé</th>
                  <th scope="col" style={{ textAlign: 'left', padding: '8px', fontSize: 12 }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredBooks.map((b) => {
                  const rows = stocks.filter((s) => s.id_livre === b.id_livre)
                  const bookCell = (
                    <div>
                      <Link href={`/admin/books/${b.id_livre}`} style={{ fontWeight: 700, textDecoration: 'none', color: 'var(--color-text)' }}>{b.titre}</Link>
                      <div className="muted" style={{ fontSize: 11 }}>ISBN {b.isbn}</div>
                    </div>
                  )
                  return (
                    <Fragment key={b.id_livre}>
                      {rows.length === 0 ? (
                        <tr key={`${b.id_livre}-empty`} style={{ borderBottom: '1px solid var(--color-border)' }}>
                          <td style={{ padding: '10px 8px', verticalAlign: 'top' }}>{bookCell}</td>
                          <td colSpan={3} className="muted" style={{ padding: '10px 8px', fontSize: 12 }}>Aucun stock enregistré</td>
                          <td />
                        </tr>
                      ) : rows.map((s) => (
                        <tr key={s.id_stock} style={{ borderBottom: '1px solid var(--color-border)' }}>
                          <td style={{ padding: '10px 8px', verticalAlign: 'top' }}>{bookCell}</td>
                          <td style={{ padding: '10px 8px', fontSize: 13, verticalAlign: 'top' }}>{sourceLabel(s.id_source_stock)}</td>
                          <td style={{ padding: '10px 8px', fontSize: 13, verticalAlign: 'top' }}>
                            <strong style={{ color: 'var(--color-text)' }}>{s.quantite_disponible}</strong>
                          </td>
                          <td style={{ padding: '10px 8px', fontSize: 13, verticalAlign: 'top' }} className="muted">{s.quantite_reservee ?? 0}</td>
                          <td style={{ padding: '10px 8px', verticalAlign: 'top' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                              <button
                                className="btn"
                                style={{ fontSize: 12, padding: '2px 8px' }}
                                disabled={busyKey === `dec-${s.id_stock}` || s.quantite_disponible <= 0}
                                onClick={() => onDecrement(s)}
                                aria-label={`Retirer un exemplaire de ${b.titre} — source ${sourceLabel(s.id_source_stock)}`}
                              >
                                −1
                              </button>
                              <button
                                className="btn"
                                style={{ fontSize: 12, padding: '2px 8px' }}
                                disabled={busyKey === `inc-${s.id_stock}`}
                                onClick={() => onIncrement(s)}
                                aria-label={`Ajouter un exemplaire de ${b.titre} — source ${sourceLabel(s.id_source_stock)}`}
                              >
                                +1
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                      {sources.length > 0 ? (
                        <tr key={`${b.id_livre}-add`} style={{ borderBottom: '1px solid var(--color-border)' }}>
                          <td style={{ padding: '6px 8px' }} className="muted" aria-hidden="true">+ nouvelle source pour {b.titre}</td>
                          <td style={{ padding: '6px 8px' }}>
                            <label htmlFor={`add-stock-source-${b.id_livre}`} className="sr-only">Nouvelle source de stock pour {b.titre}</label>
                            <select
                              id={`add-stock-source-${b.id_livre}`}
                              className="input"
                              style={{ fontSize: 12, padding: '3px 6px' }}
                              value={addStockBookId[b.id_livre] || ''}
                              onChange={(e) => setAddStockBookId((m) => ({ ...m, [b.id_livre]: e.target.value }))}
                            >
                              <option value="">+ nouvelle source de stock…</option>
                              {sources
                                .filter((s) => !rows.some((r) => r.id_source_stock === s.id_source_stock))
                                .map((s) => (
                                  <option key={s.id_source_stock} value={s.id_source_stock}>{s.libelle}</option>
                                ))}
                            </select>
                          </td>
                          <td style={{ padding: '6px 8px' }}>
                            <label htmlFor={`add-stock-qty-${b.id_livre}`} className="sr-only">Quantité initiale pour {b.titre}</label>
                            <input
                              id={`add-stock-qty-${b.id_livre}`}
                              className="input"
                              type="number"
                              min={0}
                              style={{ width: 70, fontSize: 12, padding: '3px 6px' }}
                              placeholder="qté"
                              value={addStockQty[b.id_livre] || ''}
                              onChange={(e) => setAddStockQty((m) => ({ ...m, [b.id_livre]: e.target.value }))}
                            />
                          </td>
                          <td />
                          <td style={{ padding: '6px 8px' }}>
                            <button
                              className="btn"
                              style={{ fontSize: 12, padding: '3px 10px' }}
                              disabled={!addStockBookId[b.id_livre] || busyKey === `add-${b.id_livre}`}
                              onClick={() => onAddStock(b)}
                              aria-label={`Ajouter une nouvelle source de stock pour ${b.titre}`}
                            >
                              Ajouter
                            </button>
                          </td>
                        </tr>
                      ) : null}
                    </Fragment>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  )
}
