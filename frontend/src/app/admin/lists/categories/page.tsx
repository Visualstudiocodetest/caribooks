'use client'

import { useEffect, useState } from 'react'
import { apiFetch } from '@/services/api'

type Categorie = { id_categorie: number; libelle: string }

export default function CategoriesAdmin() {
  const [list, setList] = useState<Categorie[]>([])
  const [libelle, setLibelle] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editValue, setEditValue] = useState('')

  async function load() {
    try {
      setList(await apiFetch<Categorie[]>('/catalog/categories'))
    } catch (e) {
      setError((e as Error).message)
    }
  }

  useEffect(() => { load() }, [])

  async function createOne(e: { preventDefault(): void }) {
    e.preventDefault()
    if (!libelle.trim()) return
    try {
      await apiFetch('/catalog/categories', { method: 'POST', auth: true, body: JSON.stringify({ libelle: libelle.trim() }) })
      setLibelle('')
      await load()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  async function startEdit(item: Categorie) {
    setEditingId(item.id_categorie)
    setEditValue(item.libelle)
  }

  async function saveEdit(id: number) {
    if (!editValue.trim()) return
    try {
      await apiFetch(`/catalog/categories/${id}`, { method: 'PUT', auth: true, body: JSON.stringify({ libelle: editValue.trim() }) })
      setEditingId(null)
      await load()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  async function remove(id: number) {
    if (!confirm('Supprimer cette catégorie ?')) return
    try {
      await apiFetch(`/catalog/categories/${id}`, { method: 'DELETE', auth: true })
      await load()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <div style={{ display: 'grid', gap: 14, maxWidth: 560 }}>
      <h2 style={{ margin: 0 }}>Catégories</h2>
      {error ? <div className="banner-error">{error}</div> : null}
      <form onSubmit={createOne} style={{ display: 'flex', gap: 8 }}>
        <input className="input" style={{ flex: 1 }} placeholder="Nouvelle catégorie" value={libelle} onChange={(e) => setLibelle(e.target.value)} required />
        <button className="btn btnPrimary" type="submit">Ajouter</button>
      </form>
      <div className="card" style={{ padding: 8 }}>
        {list.length === 0 ? (
          <div className="muted" style={{ padding: '8px 8px' }}>Aucune catégorie</div>
        ) : list.map((c, i) => (
          <div key={c.id_categorie} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 8px', borderBottom: i < list.length - 1 ? '1px solid var(--color-border)' : 'none' }}>
            {editingId === c.id_categorie ? (
              <>
                <input className="input" style={{ flex: 1 }} value={editValue} onChange={(e) => setEditValue(e.target.value)} autoFocus onKeyDown={(e) => { if (e.key === 'Enter') saveEdit(c.id_categorie); if (e.key === 'Escape') setEditingId(null) }} />
                <button className="btn btnPrimary" style={{ fontSize: 12, padding: '4px 10px' }} onClick={() => saveEdit(c.id_categorie)}>✓</button>
                <button className="btn" style={{ fontSize: 12, padding: '4px 10px' }} onClick={() => setEditingId(null)}>✕</button>
              </>
            ) : (
              <>
                <span style={{ flex: 1, fontWeight: 600 }}>{c.libelle}</span>
                <button className="btn" style={{ fontSize: 12, padding: '3px 10px' }} onClick={() => startEdit(c)}>Renommer</button>
                <button className="btn" style={{ fontSize: 12, padding: '3px 10px', color: '#dc2626' }} onClick={() => remove(c.id_categorie)}>Supprimer</button>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
