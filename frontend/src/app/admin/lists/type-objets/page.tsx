'use client'

import { useEffect, useState } from 'react'
import { listCatalog, createCatalogItem, updateCatalogItem, deleteCatalogItem } from '@/services/catalog'

type TypeObjet = { id_type_objet: number; libelle: string; code?: string }

export default function TypeObjetsAdmin() {
  const [list, setList] = useState<TypeObjet[]>([])
  const [libelle, setLibelle] = useState('')
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editLibelle, setEditLibelle] = useState('')
  const [editCode, setEditCode] = useState('')

  async function load() {
    try {
      setList(await listCatalog<TypeObjet>('type-objets'))
    } catch (e) {
      setError((e as Error).message)
    }
  }

  useEffect(() => { load() }, [])

  async function createOne(e: { preventDefault(): void }) {
    e.preventDefault()
    if (!libelle.trim()) return
    try {
      await createCatalogItem('type-objets', { libelle: libelle.trim(), code: code.trim() || undefined })
      setLibelle('')
      setCode('')
      await load()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  async function saveEdit(id: number) {
    if (!editLibelle.trim()) return
    try {
      await updateCatalogItem('type-objets', id, { libelle: editLibelle.trim(), code: editCode.trim() || undefined })
      setEditingId(null)
      await load()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  async function remove(id: number) {
    if (!confirm('Supprimer ce type ?')) return
    try {
      await deleteCatalogItem('type-objets', id)
      await load()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <div style={{ display: 'grid', gap: 14, maxWidth: 560 }}>
      <h1 style={{ margin: 0, fontSize: '1.5rem' }}>Types d&apos;objets</h1>
      {error ? <div className="banner-error" role="alert">{error}</div> : null}
      <form onSubmit={createOne} style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <label htmlFor="new-type-libelle" className="sr-only">Nom du nouveau type d&apos;objet</label>
        <input id="new-type-libelle" className="input" style={{ flex: '2 1 160px' }} placeholder="Nom (ex: Livre, DVD…)" value={libelle} onChange={(e) => setLibelle(e.target.value)} required />
        <label htmlFor="new-type-code" className="sr-only">Code du nouveau type d&apos;objet</label>
        <input id="new-type-code" className="input" style={{ flex: '1 1 100px' }} placeholder="Code (ex: BOOK)" value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} />
        <button className="btn btnPrimary" type="submit">Ajouter</button>
      </form>
      <h2 className="sr-only">Liste des types d&apos;objets</h2>
      <div className="card" style={{ padding: 8 }}>
        {list.length === 0 ? (
          <div className="muted" style={{ padding: '8px 8px' }}>Aucun type</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th scope="col" className="sr-only">Nom</th>
                <th scope="col" className="sr-only">Code</th>
                <th scope="col" className="sr-only">Actions</th>
              </tr>
            </thead>
            <tbody>
              {list.map((c) => (
                <tr key={c.id_type_objet} style={{ borderBottom: '1px solid var(--color-border)' }}>
                  {editingId === c.id_type_objet ? (
                    <td colSpan={3} style={{ padding: '8px 8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <label htmlFor={`edit-type-libelle-${c.id_type_objet}`} className="sr-only">Modifier le nom de {c.libelle}</label>
                        <input
                          id={`edit-type-libelle-${c.id_type_objet}`}
                          className="input"
                          style={{ flex: 2 }}
                          value={editLibelle}
                          onChange={(e) => setEditLibelle(e.target.value)}
                          autoFocus
                          onKeyDown={(e) => { if (e.key === 'Escape') setEditingId(null) }}
                        />
                        <label htmlFor={`edit-type-code-${c.id_type_objet}`} className="sr-only">Modifier le code de {c.libelle}</label>
                        <input
                          id={`edit-type-code-${c.id_type_objet}`}
                          className="input"
                          style={{ flex: 1 }}
                          value={editCode}
                          onChange={(e) => setEditCode(e.target.value.toUpperCase())}
                          placeholder="Code"
                        />
                        <button className="btn btnPrimary" style={{ fontSize: 12, padding: '4px 10px' }} onClick={() => saveEdit(c.id_type_objet)} aria-label={`Valider la modification de ${c.libelle}`}>✓</button>
                        <button className="btn" style={{ fontSize: 12, padding: '4px 10px' }} onClick={() => setEditingId(null)} aria-label={`Annuler la modification de ${c.libelle}`}>✕</button>
                      </div>
                    </td>
                  ) : (
                    <>
                      <td style={{ padding: '8px 8px', fontWeight: 600 }}>{c.libelle}</td>
                      <td style={{ padding: '8px 8px' }} className="muted">{c.code || '—'}</td>
                      <td style={{ padding: '8px 8px' }}>
                        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                          <button className="btn" style={{ fontSize: 12, padding: '3px 10px' }} onClick={() => { setEditingId(c.id_type_objet); setEditLibelle(c.libelle); setEditCode(c.code ?? '') }} aria-label={`Renommer le type ${c.libelle}`}>Renommer</button>
                          <button className="btn" style={{ fontSize: 12, padding: '3px 10px', color: '#dc2626' }} onClick={() => remove(c.id_type_objet)} aria-label={`Supprimer le type ${c.libelle}`}>Supprimer</button>
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
