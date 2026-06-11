'use client'

import { useEffect, useState } from 'react'
import { apiFetch } from '@/services/api'

type TypeObjet = { id_type_objet: number; libelle: string; code?: string }

export default function TypeObjetsAdmin() {
  const [list, setList] = useState<TypeObjet[]>([])
  const [libelle, setLibelle] = useState('')
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function load() {
    try {
      const r = await apiFetch<TypeObjet[]>('/catalog/type-objets')
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
      await apiFetch('/catalog/type-objets', { method: 'POST', auth: true, body: JSON.stringify({ libelle: libelle.trim(), code: code.trim() || undefined }) })
      setLibelle('')
      setCode('')
      await load()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  async function remove(id: number) {
    if (!confirm('Supprimer ce type ?')) return
    try {
      await apiFetch(`/catalog/type-objets/${id}`, { method: 'DELETE', auth: true })
      await load()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <div style={{ display: 'grid', gap: 14 }}>
      <h2 style={{ margin: 0 }}>Types d&apos;objets</h2>
      {error ? <div className="banner-error">{error}</div> : null}
      <form onSubmit={createOne} style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <input
          className="input"
          style={{ flex: '2 1 160px' }}
          placeholder="Nom (ex: Livre, DVD…)"
          value={libelle}
          onChange={(e) => setLibelle(e.target.value)}
          required
        />
        <input
          className="input"
          style={{ flex: '1 1 100px' }}
          placeholder="Code (ex: BOOK)"
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
        />
        <button className="btn btnPrimary" type="submit">Ajouter</button>
      </form>
      <div className="card" style={{ padding: 8, display: 'grid', gap: 0 }}>
        {list.length === 0 ? (
          <div className="muted" style={{ padding: '8px 8px' }}>Aucun type</div>
        ) : list.map((c, i) => (
          <div
            key={c.id_type_objet}
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '8px 8px',
              borderBottom: i < list.length - 1 ? '1px solid var(--color-border)' : 'none',
            }}
          >
            <div>
              <span style={{ fontWeight: 700 }}>{c.libelle}</span>
              {c.code ? <span className="muted" style={{ marginLeft: 8, fontSize: 12 }}>{c.code}</span> : null}
            </div>
            <button className="btn" style={{ fontSize: 12, padding: '3px 10px' }} onClick={() => remove(c.id_type_objet)}>
              Supprimer
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
