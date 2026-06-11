'use client'

import { useEffect, useState } from 'react'
import { apiFetch } from '@/services/api'

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
      setList(await apiFetch<TypeObjet[]>('/catalog/type-objets'))
    } catch (e) {
      setError((e as Error).message)
    }
  }

  useEffect(() => { load() }, [])

  async function createOne(e: { preventDefault(): void }) {
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

  async function saveEdit(id: number) {
    if (!editLibelle.trim()) return
    try {
      await apiFetch(`/catalog/type-objets/${id}`, { method: 'PUT', auth: true, body: JSON.stringify({ libelle: editLibelle.trim(), code: editCode.trim() || undefined }) })
      setEditingId(null)
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
    <div style={{ display: 'grid', gap: 14, maxWidth: 560 }}>
      <h2 style={{ margin: 0 }}>Types d&apos;objets</h2>
      {error ? <div className="banner-error">{error}</div> : null}
      <form onSubmit={createOne} style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <input className="input" style={{ flex: '2 1 160px' }} placeholder="Nom (ex: Livre, DVD…)" value={libelle} onChange={(e) => setLibelle(e.target.value)} required />
        <input className="input" style={{ flex: '1 1 100px' }} placeholder="Code (ex: BOOK)" value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} />
        <button className="btn btnPrimary" type="submit">Ajouter</button>
      </form>
      <div className="card" style={{ padding: 8 }}>
        {list.length === 0 ? (
          <div className="muted" style={{ padding: '8px 8px' }}>Aucun type</div>
        ) : list.map((c, i) => (
          <div key={c.id_type_objet} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 8px', borderBottom: i < list.length - 1 ? '1px solid var(--color-border)' : 'none' }}>
            {editingId === c.id_type_objet ? (
              <>
                <input className="input" style={{ flex: 2 }} value={editLibelle} onChange={(e) => setEditLibelle(e.target.value)} autoFocus onKeyDown={(e) => { if (e.key === 'Escape') setEditingId(null) }} />
                <input className="input" style={{ flex: 1 }} value={editCode} onChange={(e) => setEditCode(e.target.value.toUpperCase())} placeholder="Code" />
                <button className="btn btnPrimary" style={{ fontSize: 12, padding: '4px 10px' }} onClick={() => saveEdit(c.id_type_objet)}>✓</button>
                <button className="btn" style={{ fontSize: 12, padding: '4px 10px' }} onClick={() => setEditingId(null)}>✕</button>
              </>
            ) : (
              <>
                <span style={{ flex: 1, fontWeight: 600 }}>{c.libelle}</span>
                {c.code ? <span className="muted" style={{ fontSize: 12 }}>{c.code}</span> : null}
                <button className="btn" style={{ fontSize: 12, padding: '3px 10px' }} onClick={() => { setEditingId(c.id_type_objet); setEditLibelle(c.libelle); setEditCode(c.code ?? '') }}>Renommer</button>
                <button className="btn" style={{ fontSize: 12, padding: '3px 10px', color: '#dc2626' }} onClick={() => remove(c.id_type_objet)}>Supprimer</button>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
