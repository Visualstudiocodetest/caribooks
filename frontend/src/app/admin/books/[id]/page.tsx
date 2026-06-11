'use client'

import { useEffect, useState, use } from 'react'
import { useRouter } from 'next/navigation'
import type { BookRead } from '@/types/api'
import { ApiError } from '@/services/api'
import { deleteBook, getBook, updateBook } from '@/services/books'

export default function AdminEditBookPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: idStr } = use(params)
  const router = useRouter()
  const id = Number(idStr)
  const [book, setBook] = useState<BookRead | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    let mounted = true
    getBook(id)
      .then((b) => {
        if (!mounted) return
        setBook(b)
      })
      .catch((e: unknown) => {
        if (!mounted) return
        setError(e instanceof ApiError ? e.message : 'Erreur')
      })
    return () => {
      mounted = false
    }
  }, [id])

  async function onSave() {
    if (!book) return
    setSaving(true)
    setError(null)
    try {
      const updated = await updateBook(id, {
        titre: book.titre,
        isbn: book.isbn,
        auteur: book.auteur,
        prix_chf: book.prix_chf,
        actif: book.actif,
        image_link: book.image_link,
        description: book.description,
      })
      setBook(updated)
    } catch (e) {
      const err = e as unknown
      setError(err instanceof ApiError ? err.message : 'Sauvegarde impossible')
    } finally {
      setSaving(false)
    }
  }

  async function onDelete() {
    if (!confirm('Supprimer ce livre ?')) return
    setDeleting(true)
    setError(null)
    try {
      await deleteBook(id)
      router.push('/admin/books')
    } catch (e) {
      const err = e as unknown
      setError(err instanceof ApiError ? err.message : 'Suppression impossible')
    } finally {
      setDeleting(false)
    }
  }

  if (!book) {
    return <div className="muted">Chargement…</div>
  }

  return (
    <div style={{ maxWidth: 820, margin: '0 auto', display: 'grid', gap: 14 }}>
      <h1 style={{ margin: 0 }}>Modifier</h1>

      <div className="card" style={{ padding: 16, display: 'grid', gap: 12 }}>
        <input
          className="input"
          value={book.titre}
          onChange={(e) => setBook({ ...book, titre: e.target.value })}
          placeholder="Titre"
        />
        <input
          className="input"
          value={book.isbn}
          onChange={(e) => setBook({ ...book, isbn: e.target.value })}
          placeholder="ISBN"
        />
        <input
          className="input"
          value={book.auteur ?? ''}
          onChange={(e) => setBook({ ...book, auteur: e.target.value || null })}
          placeholder="Auteur"
        />
        <input
          className="input"
          value={String(book.prix_chf)}
          onChange={(e) => setBook({ ...book, prix_chf: Number(e.target.value) })}
          placeholder="Prix CHF"
        />
        <input
          className="input"
          value={book.image_link ?? ''}
          onChange={(e) => setBook({ ...book, image_link: e.target.value || null })}
          placeholder="Image URL (optionnel)"
        />
        <textarea
          className="card"
          style={{ borderRadius: 14, padding: 12, borderColor: 'var(--color-border)', minHeight: 120 }}
          value={book.description ?? ''}
          onChange={(e) => setBook({ ...book, description: e.target.value || null })}
          placeholder="Description"
        />
        <label style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <input
            type="checkbox"
            checked={book.actif}
            onChange={(e) => setBook({ ...book, actif: e.target.checked })}
          />
          <span>Actif</span>
        </label>

        {error ? <div className="banner-error">{error}</div> : null}

        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'space-between' }}>
          <button className="btn btnPrimary" type="button" onClick={onSave} disabled={saving}>
            {saving ? 'Sauvegarde…' : 'Sauvegarder'}
          </button>
          <button className="btn" type="button" onClick={onDelete} disabled={deleting}>
            {deleting ? 'Suppression…' : 'Supprimer'}
          </button>
        </div>

      </div>
    </div>
  )
}
