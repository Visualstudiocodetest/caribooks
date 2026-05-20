'use client'

import { useMemo, useState, useEffect } from 'react'
import type { BookRead } from '@/types/api'
import { BookGrid } from '@/components/books/BookGrid'
import { apiFetch } from '@/services/api'

export function CatalogClient({ books }: { books: BookRead[] }) {
  const [query, setQuery] = useState('')
  const [etatList, setEtatList] = useState<any[]>([])
  const [categorieList, setCategorieList] = useState<any[]>([])
  const [selectedEtat, setSelectedEtat] = useState('')
  const [selectedCategorie, setSelectedCategorie] = useState('')
  const [sortBy, setSortBy] = useState('')

  useEffect(() => {
    let mounted = true
    async function load() {
      try {
        const etats = await apiFetch('/catalog/etat-usures')
        if (mounted && Array.isArray(etats)) setEtatList(etats as any[])
      } catch {}
      try {
        const cats = await apiFetch('/catalog/categories')
        if (mounted && Array.isArray(cats)) setCategorieList(cats as any[])
      } catch {}
    }
    void load()
    return () => {
      mounted = false
    }
  }, [])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()

    let res = books.filter((b) => {
      if (q) {
        const hay = `${b.titre} ${b.auteur ?? ''} ${b.isbn}`.toLowerCase()
        if (!hay.includes(q)) return false
      }
      if (selectedEtat) {
        // some items may not have the field yet
        if (!('id_etat_usure' in b) || String((b as any).id_etat_usure) !== selectedEtat) return false
      }
      if (selectedCategorie) {
        const ids = Array.isArray((b as any).categorie_ids) ? (b as any).categorie_ids.map(String) : []
        if (!ids.includes(selectedCategorie)) return false
      }
      return true
    })

    if (sortBy) {
      res = res.slice().sort((a, b) => {
        if (sortBy === 'auteur') return String(a.auteur || '').localeCompare(String(b.auteur || ''))
        if (sortBy === 'titre') return String(a.titre || '').localeCompare(String(b.titre || ''))
        if (sortBy === 'date') {
          const ta = a.date_creation ? new Date(a.date_creation).getTime() : 0
          const tb = b.date_creation ? new Date(b.date_creation).getTime() : 0
          return tb - ta // newest first
        }
        if (sortBy === 'categorie') {
          const aCatId = Array.isArray((a as any).categorie_ids) && (a as any).categorie_ids.length ? (a as any).categorie_ids[0] : null
          const bCatId = Array.isArray((b as any).categorie_ids) && (b as any).categorie_ids.length ? (b as any).categorie_ids[0] : null
          const aLabel = aCatId ? (categorieList.find((c) => c.id_categorie === aCatId)?.libelle || '') : ''
          const bLabel = bCatId ? (categorieList.find((c) => c.id_categorie === bCatId)?.libelle || '') : ''
          return String(aLabel).localeCompare(String(bLabel))
        }
        return 0
      })
    }

    return res
  }, [books, query, selectedEtat, selectedCategorie, sortBy, categorieList])

  return (
    <div style={{ display: 'grid', gap: 14 }}>
      <div className="card" style={{ padding: 14, display: 'grid', gap: 10 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <h1 style={{ margin: 0 }}>Catalogue</h1>
          <div className="muted" style={{ alignSelf: 'end' }}>
            {filtered.length} résultat(s)
          </div>
        </div>

        <div style={{ display: 'grid', gap: 8 }}>
          <input
            className="input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Rechercher par titre, auteur ou ISBN"
          />

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <select className="input" value={selectedEtat} onChange={(e) => setSelectedEtat(e.target.value)}>
              <option value="">État</option>
              {etatList.map((et) => (
                <option key={et.id_etat_usure} value={String(et.id_etat_usure)}>
                  {et.libelle}
                </option>
              ))}
            </select>

            <select className="input" value={selectedCategorie} onChange={(e) => setSelectedCategorie(e.target.value)}>
              <option value="">Toutes catégories</option>
              {categorieList.map((c) => (
                <option key={c.id_categorie} value={String(c.id_categorie)}>
                  {c.libelle}
                </option>
              ))}
            </select>

            <select className="input" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
              <option value="">Ordre par</option>
              <option value="auteur">Auteur</option>
              <option value="date">Date d'ajout</option>
              <option value="titre">Titre</option>
              <option value="categorie">Catégorie</option>
            </select>
          </div>
        </div>
      </div>

      <BookGrid books={filtered} />
    </div>
  )
}
