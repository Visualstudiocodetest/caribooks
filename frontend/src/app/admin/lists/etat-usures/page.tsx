'use client'

import { useEffect, useState } from 'react'
import { apiFetch } from '@/services/api'

type Etat = { id_etat_usure: number; libelle: string }

export default function EtatUsuresAdmin() {
  const [list, setList] = useState<Etat[]>([])
  const [libelle, setLibelle] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function load() {
    try {
      const r = await apiFetch<Etat[]>('/catalog/etat-usures')
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
      await apiFetch('/catalog/etat-usures', { method: 'POST', auth: true, body: JSON.stringify({ libelle: libelle.trim() }) })
      setLibelle('')
      await load()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  async function remove(id: number) {
    if (!confirm('Supprimer cet état ?')) return
    try {
      await apiFetch(`/catalog/etat-usures/${id}`, { method: 'DELETE', auth: true })
      await load()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <div style={{ display: 'grid', gap: 14 }}>
      <h2 style={{ margin: 0 }}>États d&apos;usure</h2>
      {error ? <div className="banner-error">{error}</div> : null}
      <form onSubmit={createOne} style={{ display: 'flex', gap: 8 }}>
        <input
          className="input"
          style={{ flex: 1 }}
          placeholder="Nom de l'état (ex: Neuf, Bon état…)"
          value={libelle}
          onChange={(e) => setLibelle(e.target.value)}
          required
        />
        <button className="btn btnPrimary" type="submit">Ajouter</button>
      </form>
      <div className="card" style={{ padding: 8, display: 'grid', gap: 0 }}>
        {list.length === 0 ? (
          <div className="muted" style={{ padding: '8px 8px' }}>Aucun état</div>
        ) : list.map((c, i) => (
          <div
            key={c.id_etat_usure}
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '8px 8px',
              borderBottom: i < list.length - 1 ? '1px solid var(--color-border)' : 'none',
            }}
          >
            <span style={{ fontWeight: 700 }}>{c.libelle}</span>
            <button className="btn" style={{ fontSize: 12, padding: '3px 10px' }} onClick={() => remove(c.id_etat_usure)}>
              Supprimer
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
