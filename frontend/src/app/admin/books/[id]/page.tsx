'use client'

import { useEffect, useState, use } from 'react'
import { useRouter } from 'next/navigation'
import type { BookRead } from '@/types/api'
import { ApiError } from '@/services/api'
import { deleteBook, getBook, updateBook } from '@/services/books'
import { listCatalog } from '@/services/catalog'

type EtatItem = { id_etat_usure: number; libelle: string }
type CategorieItem = { id_categorie: number; libelle: string }

export default function AdminEditBookPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: idStr } = use(params)
  const router = useRouter()
  const id = Number(idStr)

  const [book, setBook] = useState<BookRead | null>(null)
  const [etats, setEtats] = useState<EtatItem[]>([])
  const [categories, setCategories] = useState<CategorieItem[]>([])
  const [selectedCats, setSelectedCats] = useState<number[]>([])
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    let mounted = true
    Promise.all([
      getBook(id),
      listCatalog<EtatItem>('etat-usures').catch(() => []),
      listCatalog<CategorieItem>('categories').catch(() => []),
    ]).then(([b, e, c]) => {
      if (!mounted) return
      setBook(b)
      setEtats(e)
      setCategories(c)
      setSelectedCats(b.categorie_ids ?? [])
    }).catch((e: unknown) => {
      if (!mounted) return
      setError(e instanceof ApiError ? e.message : 'Erreur de chargement')
    })
    return () => { mounted = false }
  }, [id])

  function toggleCat(id: number) {
    setSelectedCats((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id])
  }

  async function onSave() {
    if (!book) return
    setSaving(true)
    setError(null)
    setSaved(false)
    try {
      const updated = await updateBook(id, {
        titre: book.titre,
        isbn: book.isbn,
        auteur: book.auteur,
        editeur: book.editeur,
        date_publication: book.date_publication,
        langue: book.langue,
        prix_chf: book.prix_chf,
        actif: book.actif,
        image_link: book.image_link,
        description: book.description,
        id_etat_usure: book.id_etat_usure,
        categorie_ids: selectedCats,
      })
      setBook(updated)
      setSelectedCats(updated.categorie_ids ?? [])
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Sauvegarde impossible')
    } finally {
      setSaving(false)
    }
  }

  async function onDelete() {
    if (!confirm('Supprimer ce livre définitivement ?')) return
    setDeleting(true)
    try {
      await deleteBook(id)
      router.push('/admin/books')
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Suppression impossible')
      setDeleting(false)
    }
  }

  if (!book && !error) return <div className="muted">Chargement…</div>
  if (error && !book) return <div className="banner-error">{error}</div>
  if (!book) return null

  return (
    <div style={{ maxWidth: 680, margin: '0 auto', display: 'grid', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <button className="btn" onClick={() => router.push('/admin/books')} style={{ fontSize: 13 }}>← Retour</button>
        <h1 style={{ margin: 0, fontSize: '1.3rem' }}>Modifier le livre</h1>
      </div>

      {error ? <div className="banner-error">{error}</div> : null}
      {saved ? <div style={{ background: '#d1fae5', color: '#065f46', padding: '10px 14px', borderRadius: 10, fontWeight: 600, fontSize: 14 }}>✓ Sauvegardé</div> : null}

      <div className="card" style={{ padding: 20, display: 'grid', gap: 14 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <div style={{ gridColumn: '1 / -1' }}>
            <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 4 }}>Titre *</label>
            <input className="input" value={book.titre} onChange={(e) => setBook({ ...book, titre: e.target.value })} placeholder="Titre" />
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 4 }}>ISBN *</label>
            <input className="input" value={book.isbn} onChange={(e) => setBook({ ...book, isbn: e.target.value })} placeholder="ISBN" />
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 4 }}>Prix (CHF) *</label>
            <input className="input" type="number" step="0.01" min="0" value={book.prix_chf} onChange={(e) => setBook({ ...book, prix_chf: Number(e.target.value) })} placeholder="Prix" />
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 4 }}>Auteur</label>
            <input className="input" value={book.auteur ?? ''} onChange={(e) => setBook({ ...book, auteur: e.target.value || null })} placeholder="Auteur" />
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 4 }}>Éditeur</label>
            <input className="input" value={book.editeur ?? ''} onChange={(e) => setBook({ ...book, editeur: e.target.value || null })} placeholder="Éditeur" />
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 4 }}>Date de publication</label>
            <input className="input" value={book.date_publication ?? ''} onChange={(e) => setBook({ ...book, date_publication: e.target.value || null })} placeholder="ex: 2021" />
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 4 }}>Langue</label>
            <input className="input" value={book.langue ?? ''} onChange={(e) => setBook({ ...book, langue: e.target.value || null })} placeholder="ex: fr, en" />
          </div>
          {etats.length > 0 ? (
            <div>
              <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 4 }}>État</label>
              <select className="input" value={book.id_etat_usure ?? ''} onChange={(e) => setBook({ ...book, id_etat_usure: Number(e.target.value) })}>
                <option value="">— Choisir —</option>
                {etats.map((et) => (
                  <option key={et.id_etat_usure} value={et.id_etat_usure}>{et.libelle}</option>
                ))}
              </select>
            </div>
          ) : null}
          <div style={{ gridColumn: '1 / -1' }}>
            <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 4 }}>URL image</label>
            <input className="input" value={book.image_link ?? ''} onChange={(e) => setBook({ ...book, image_link: e.target.value || null })} placeholder="https://…" />
          </div>
          <div style={{ gridColumn: '1 / -1' }}>
            <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 4 }}>Description</label>
            <textarea
              style={{ width: '100%', borderRadius: 10, padding: 10, border: '1px solid var(--color-border)', minHeight: 100, fontFamily: 'inherit', fontSize: 14, resize: 'vertical' }}
              value={book.description ?? ''}
              onChange={(e) => setBook({ ...book, description: e.target.value || null })}
              placeholder="Description…"
            />
          </div>
          {categories.length > 0 ? (
            <div style={{ gridColumn: '1 / -1' }}>
              <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 8 }}>Catégories</label>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {categories.map((c) => {
                  const checked = selectedCats.includes(c.id_categorie)
                  return (
                    <button
                      key={c.id_categorie}
                      type="button"
                      onClick={() => toggleCat(c.id_categorie)}
                      style={{ padding: '4px 12px', borderRadius: 999, fontSize: 13, fontWeight: 600, border: '1.5px solid', cursor: 'pointer', background: checked ? 'var(--color-primary)' : 'transparent', color: checked ? 'white' : 'var(--color-text)', borderColor: checked ? 'var(--color-primary)' : 'var(--color-border)' }}
                    >
                      {c.libelle}
                    </button>
                  )
                })}
              </div>
            </div>
          ) : null}
          <div style={{ gridColumn: '1 / -1' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <input type="checkbox" checked={book.actif} onChange={(e) => setBook({ ...book, actif: e.target.checked })} />
              <span style={{ fontWeight: 600 }}>Actif (visible dans le catalogue)</span>
            </label>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'space-between', paddingTop: 8, borderTop: '1px solid var(--color-border)' }}>
          <button className="btn btnPrimary" type="button" onClick={onSave} disabled={saving}>
            {saving ? 'Sauvegarde…' : 'Sauvegarder'}
          </button>
          <button className="btn" type="button" onClick={onDelete} disabled={deleting} style={{ color: '#dc2626' }}>
            {deleting ? 'Suppression…' : 'Supprimer'}
          </button>
        </div>
      </div>
    </div>
  )
}
