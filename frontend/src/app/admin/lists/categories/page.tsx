'use client'

import { useEffect, useState } from 'react'
import { apiFetch } from '@/services/api'

type Categorie = { id_categorie: number; libelle: string }

export default function CategoriesAdmin() {
  const [list, setList] = useState<Categorie[]>([])
  const [libelle, setLibelle] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function load() {
    try {
      const r = await apiFetch<Categorie[]>('/catalog/categories')
      setList(r)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  useEffect(() => { load() }, [])

  async function createOne(e: React.FormEvent) {
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
    <div style={{ display: 'grid', gap: 14 }}>
      <h2 style={{ margin: 0 }}>Catégories</h2>
      {error ? <div className="banner-error">{error}</div> : null}
      <form onSubmit={createOne} style={{ display: 'flex', gap: 8 }}>
        <input
          className="input"
          style={{ flex: 1 }}
          placeholder="Nom de la catégorie"
          value={libelle}
          onChange={(e) => setLibelle(e.target.value)}
          required
        />
        <button className="btn btnPrimary" type="submit">Ajouter</button>
      </form>
      <div className="card" style={{ padding: 8, display: 'grid', gap: 0 }}>
        {list.length === 0 ? (
          <div className="muted" style={{ padding: '8px 8px' }}>Aucune catégorie</div>
        ) : list.map((c, i) => (
          <div
            key={c.id_categorie}
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '8px 8px',
              borderBottom: i < list.length - 1 ? '1px solid var(--color-border)' : 'none',
            }}
          >
            <span style={{ fontWeight: 700 }}>{c.libelle}</span>
            <button className="btn" style={{ fontSize: 12, padding: '3px 10px' }} onClick={() => remove(c.id_categorie)}>
              Supprimer
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
