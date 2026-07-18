'use client'

import { useMemo, useState, useEffect } from 'react'
import type { BookRead } from '@/types/api'
import { BookGrid } from '@/components/books/BookGrid'
import { listCatalog } from '@/services/catalog'

type EtatItem = { id_etat_usure: number; libelle: string }
type CategorieItem = { id_categorie: number; libelle: string }

export function CatalogClient({
  books,
  availability,
}: {
  books: BookRead[]
  availability?: Record<number, number>
}) {
  const [query, setQuery] = useState('')
  const [etatList, setEtatList] = useState<EtatItem[]>([])
  const [categorieList, setCategorieList] = useState<CategorieItem[]>([])
  const [selectedEtat, setSelectedEtat] = useState('')
  const [selectedCategorie, setSelectedCategorie] = useState('')
  const [sortBy, setSortBy] = useState('')
  const [minPrix, setMinPrix] = useState('')
  const [maxPrix, setMaxPrix] = useState('')
  const [showFilters, setShowFilters] = useState(false)

  useEffect(() => {
    let mounted = true
    async function load() {
      try {
        const etats = await listCatalog<EtatItem>('etat-usures')
        if (mounted && Array.isArray(etats)) setEtatList(etats)
      } catch {}
      try {
        const cats = await listCatalog<CategorieItem>('categories')
        if (mounted && Array.isArray(cats)) setCategorieList(cats)
      } catch {}
    }
    void load()
    return () => { mounted = false }
  }, [])

  const activeFilterCount = [selectedEtat, selectedCategorie, sortBy, minPrix, maxPrix].filter(Boolean).length
  const hasActiveFilters = activeFilterCount > 0

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    const min = minPrix ? Number(minPrix) : null
    const max = maxPrix ? Number(maxPrix) : null

    let res = books.filter((b) => {
      if (q) {
        const hay = `${b.titre} ${b.auteur ?? ''} ${b.isbn}`.toLowerCase()
        if (!hay.includes(q)) return false
      }
      if (selectedEtat && String(b.id_etat_usure) !== selectedEtat) return false
      if (selectedCategorie && !b.categorie_ids.map(String).includes(selectedCategorie)) return false
      if (min !== null && b.prix_chf < min) return false
      if (max !== null && b.prix_chf > max) return false
      return true
    })

    if (sortBy) {
      res = res.slice().sort((a, b) => {
        if (sortBy === 'prix_asc') return a.prix_chf - b.prix_chf
        if (sortBy === 'prix_desc') return b.prix_chf - a.prix_chf
        if (sortBy === 'auteur') return String(a.auteur || '').localeCompare(String(b.auteur || ''))
        if (sortBy === 'titre') return String(a.titre || '').localeCompare(String(b.titre || ''))
        if (sortBy === 'date') {
          const ta = a.date_creation ? new Date(a.date_creation).getTime() : 0
          const tb = b.date_creation ? new Date(b.date_creation).getTime() : 0
          return tb - ta
        }
        return 0
      })
    }

    return res
  }, [books, query, selectedEtat, selectedCategorie, sortBy, minPrix, maxPrix])

  function clearFilters() {
    setSelectedEtat('')
    setSelectedCategorie('')
    setSortBy('')
    setMinPrix('')
    setMaxPrix('')
  }

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      {/* Search bar */}
      <div style={{ display: 'flex', gap: 8 }}>
        <input
          className="input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Rechercher par titre, auteur ou ISBN…"
          style={{ flex: 1 }}
        />
        <button
          className={`btn ${hasActiveFilters ? 'btnPrimary' : 'btnGhost'}`}
          type="button"
          onClick={() => setShowFilters((s) => !s)}
          aria-expanded={showFilters}
        >
          Filtres{hasActiveFilters ? ` (${activeFilterCount})` : ''}
        </button>
      </div>

      {/* Filter panel */}
      {showFilters ? (
        <div className="card" style={{ padding: '12px 16px', display: 'grid', gap: 10 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            <select
              className="input"
              value={selectedEtat}
              onChange={(e) => setSelectedEtat(e.target.value)}
              style={{ flex: '1 1 160px' }}
            >
              <option value="">Tous les états</option>
              {etatList.map((et) => (
                <option key={et.id_etat_usure} value={String(et.id_etat_usure)}>
                  {et.libelle}
                </option>
              ))}
            </select>

            <select
              className="input"
              value={selectedCategorie}
              onChange={(e) => setSelectedCategorie(e.target.value)}
              style={{ flex: '1 1 160px' }}
            >
              <option value="">Toutes catégories</option>
              {categorieList.map((c) => (
                <option key={c.id_categorie} value={String(c.id_categorie)}>
                  {c.libelle}
                </option>
              ))}
            </select>

            <select
              className="input"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              style={{ flex: '1 1 160px' }}
            >
              <option value="">Trier par…</option>
              <option value="date">Plus récents</option>
              <option value="prix_asc">Prix croissant</option>
              <option value="prix_desc">Prix décroissant</option>
              <option value="titre">Titre A→Z</option>
              <option value="auteur">Auteur A→Z</option>
            </select>
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
            <input
              className="input"
              type="number"
              min={0}
              inputMode="decimal"
              value={minPrix}
              onChange={(e) => setMinPrix(e.target.value)}
              placeholder="Prix min (CHF)"
              aria-label="Prix minimum en CHF"
              style={{ flex: '1 1 140px' }}
            />
            <input
              className="input"
              type="number"
              min={0}
              inputMode="decimal"
              value={maxPrix}
              onChange={(e) => setMaxPrix(e.target.value)}
              placeholder="Prix max (CHF)"
              aria-label="Prix maximum en CHF"
              style={{ flex: '1 1 140px' }}
            />
          </div>

          {hasActiveFilters ? (
            <button className="btn btnGhost" type="button" onClick={clearFilters} style={{ justifySelf: 'start', padding: '4px 10px' }}>
              Effacer les filtres
            </button>
          ) : null}
        </div>
      ) : null}

      {/* Results header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ margin: 0, fontSize: '1.4rem' }}>Catalogue</h1>
        <span className="muted" style={{ fontSize: 14 }}>
          {filtered.length} livre{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      {filtered.length === 0 ? (
        <div className="card cardPadding" style={{ textAlign: 'center' }}>
          <div className="muted">Aucun livre ne correspond à votre recherche.</div>
          {(query || hasActiveFilters) ? (
            <button className="btn" type="button" onClick={() => { setQuery(''); clearFilters() }} style={{ marginTop: 10 }}>
              Réinitialiser
            </button>
          ) : null}
        </div>
      ) : (
        <BookGrid books={filtered} availability={availability} />
      )}
    </div>
  )
}
