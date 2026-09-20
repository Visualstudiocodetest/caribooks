'use client'

import { useEffect, useState } from 'react'
import { listCatalog, createCatalogItem, updateCatalogItem, deleteCatalogItem } from '@/services/catalog'

type Etat = { id_etat_usure: number; libelle: string }

export default function EtatUsuresAdmin() {
  const [list, setList] = useState<Etat[]>([])
  const [libelle, setLibelle] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editValue, setEditValue] = useState('')

  async function load() {
    try {
      setList(await listCatalog<Etat>('etat-usures'))
    } catch (e) {
      setError((e as Error).message)
    }
  }

  useEffect(() => { load() }, [])

  async function createOne(e: { preventDefault(): void }) {
    e.preventDefault()
    if (!libelle.trim()) return
    try {
      await createCatalogItem('etat-usures', { libelle: libelle.trim() })
      setLibelle('')
      await load()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  async function saveEdit(id: number) {
    if (!editValue.trim()) return
    try {
      await updateCatalogItem('etat-usures', id, { libelle: editValue.trim() })
      setEditingId(null)
      await load()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  async function remove(id: number) {
    if (!confirm('Supprimer cet état ?')) return
    try {
      await deleteCatalogItem('etat-usures', id)
      await load()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <div style={{ display: 'grid', gap: 14, maxWidth: 560 }}>
      <h1 style={{ margin: 0, fontSize: '1.5rem' }}>États d&apos;usure</h1>
      {error ? <div className="banner-error" role="alert">{error}</div> : null}
      <form onSubmit={createOne} style={{ display: 'flex', gap: 8 }}>
        <label htmlFor="new-etat-libelle" className="sr-only">Libellé du nouvel état d&apos;usure</label>
        <input id="new-etat-libelle" className="input" style={{ flex: 1 }} placeholder="ex: Neuf, Bon état, Acceptable…" value={libelle} onChange={(e) => setLibelle(e.target.value)} required />
        <button className="btn btnPrimary" type="submit">Ajouter</button>
      </form>
      <h2 className="sr-only">Liste des états d&apos;usure</h2>
      <div className="card" style={{ padding: 8 }}>
        {list.length === 0 ? (
          <div className="muted" style={{ padding: '8px 8px' }}>Aucun état</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th scope="col" className="sr-only">Libellé</th>
                <th scope="col" className="sr-only">Actions</th>
              </tr>
            </thead>
            <tbody>
              {list.map((c) => (
                <tr key={c.id_etat_usure} style={{ borderBottom: '1px solid var(--color-border)' }}>
                  {editingId === c.id_etat_usure ? (
                    <td colSpan={2} style={{ padding: '8px 8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <label htmlFor={`edit-etat-${c.id_etat_usure}`} className="sr-only">Modifier le libellé de {c.libelle}</label>
                        <input
                          id={`edit-etat-${c.id_etat_usure}`}
                          className="input"
                          style={{ flex: 1 }}
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          autoFocus
                          onKeyDown={(e) => { if (e.key === 'Enter') saveEdit(c.id_etat_usure); if (e.key === 'Escape') setEditingId(null) }}
                        />
                        <button className="btn btnPrimary" style={{ fontSize: 12, padding: '4px 10px' }} onClick={() => saveEdit(c.id_etat_usure)} aria-label={`Valider la modification de ${c.libelle}`}>✓</button>
                        <button className="btn" style={{ fontSize: 12, padding: '4px 10px' }} onClick={() => setEditingId(null)} aria-label={`Annuler la modification de ${c.libelle}`}>✕</button>
                      </div>
                    </td>
                  ) : (
                    <>
                      <td style={{ padding: '8px 8px', fontWeight: 600 }}>{c.libelle}</td>
                      <td style={{ padding: '8px 8px' }}>
                        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                          <button className="btn" style={{ fontSize: 12, padding: '3px 10px' }} onClick={() => { setEditingId(c.id_etat_usure); setEditValue(c.libelle) }} aria-label={`Renommer l'état ${c.libelle}`}>Renommer</button>
                          <button className="btn" style={{ fontSize: 12, padding: '3px 10px', color: '#dc2626' }} onClick={() => remove(c.id_etat_usure)} aria-label={`Supprimer l'état ${c.libelle}`}>Supprimer</button>
                        </div>
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
