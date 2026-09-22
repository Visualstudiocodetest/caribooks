'use client'

import { useEffect, useState, useRef, useCallback } from 'react'
import Link from 'next/link'
import { ApiError } from '@/services/api'
import { createBook, getBookByIsbn } from '@/services/books'
import { createScan } from '@/services/scans'
import { listCatalog } from '@/services/catalog'
import { listSources } from '@/services/stocks'
import Image from 'next/image'
import { lookupIsbn } from '@/services/openlibrary'
import { fetchRemoteImage, uploadLocalImage } from '@/services/images'
import { cleanIsbn } from '@/lib/isbn'
import { isExternalImage } from '@/lib/images'
import { useBarcodeScanner } from '@/hooks/useBarcodeScanner'
import type { BookRead, SourceStock } from '@/types/api'

type EtatItem = { id_etat_usure: number; libelle: string }
type TypeObjetItem = { id_type_objet: number; libelle: string; code?: string }

export default function AdminNewBookPage() {
  const [titre, setTitre] = useState('')
  const [isbn, setIsbn] = useState('')
  const [auteur, setAuteur] = useState('')
  const [prix, setPrix] = useState('')
  const [idEtat, setIdEtat] = useState('')
  const [idType, setIdType] = useState('')
  const [idSource, setIdSource] = useState('')
  const [etatList, setEtatList] = useState<EtatItem[]>([])
  const [typeList, setTypeList] = useState<TypeObjetItem[]>([])
  const [sourceList, setSourceList] = useState<SourceStock[]>([])
  const [imageLink, setImageLink] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [invalidFields, setInvalidFields] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(false)
  const [autofillLoading, setAutofillLoading] = useState(false)
  const [photoUploading, setPhotoUploading] = useState(false)
  // Set when the scanned/typed ISBN already matches a book in the Caribooks
  // catalog: creating it again would just fail on the unique ISBN constraint,
  // so instead we show the existing book and offer to log a traceability scan
  // (scan_isbn) against it, exactly like the old standalone /scan page did.
  const [existingBook, setExistingBook] = useState<BookRead | null>(null)
  const [scanSaving, setScanSaving] = useState(false)
  const [scanSaved, setScanSaved] = useState<string | null>(null)
  // Set right after a successful creation. Replaces the form with a
  // confirmation + "add another book" screen instead of navigating away, so
  // a volunteer scanning a whole box of books never leaves this page.
  const [created, setCreated] = useState<BookRead | null>(null)
  const videoRef = useRef<HTMLVideoElement | null>(null)

  function defaultTypeId(): string {
    const def = typeList.find((t) => t.code === 'BOOK' || (t.libelle || '').toLowerCase() === 'livre')
    return def ? String(def.id_type_objet) : ''
  }

  // Last-added source (end of the list, ordered by id_source_stock ascending
  // by the backend) is the one most likely to still be in active use — pre-select it.
  function defaultSourceId(): string {
    const last = sourceList[sourceList.length - 1]
    return last ? String(last.id_source_stock) : ''
  }

  function resetForm() {
    setTitre('')
    setIsbn('')
    setAuteur('')
    setPrix('')
    setIdEtat('')
    setIdType(defaultTypeId())
    setIdSource(defaultSourceId())
    setImageLink('')
    setDescription('')
    setError(null)
    setInvalidFields(new Set())
    setExistingBook(null)
    setScanSaved(null)
    setCreated(null)
  }

  async function autofill(isbnValue: string) {
    setError(null)
    setAutofillLoading(true)
    try {
      const data = await lookupIsbn(isbnValue)
      if (!data) {
        setError('Aucune donnée trouvée sur OpenLibrary pour cet ISBN.')
        return
      }
      const title = [data.title, data.subtitle].filter(Boolean).join(' — ')
      if (title) setTitre(title)
      const author = data.authors?.map((a) => a.name).filter(Boolean).join(', ')
      if (author) setAuteur(author)
      // Preview the raw OpenLibrary cover URL immediately — <Image unoptimized>
      // hotlinks it directly, no backend round trip needed just to show it.
      // The actual download-and-store-locally step (fetchRemoteImage) only
      // needs to happen once, at submit time (see onSubmit), which is also
      // where it already runs. Doing it here too used to make every single
      // scan wait ~1-2s for a full image transfer before the form even
      // showed the title/author, on top of the OpenLibrary lookup itself.
      const cover = data.cover?.large || data.cover?.medium || data.cover?.small
      if (cover) setImageLink(cover)
      const desc = typeof data.notes === 'string' ? data.notes : ''
      if (desc) setDescription(desc)
    } catch {
      setError('Impossible de contacter OpenLibrary.')
    } finally {
      setAutofillLoading(false)
    }
  }

  async function handleIsbn(cleaned: string) {
    setIsbn(cleaned)
    setScanSaved(null)
    if (!cleaned) {
      setExistingBook(null)
      return
    }
    const found = await getBookByIsbn(cleaned).catch(() => null)
    if (found) {
      setExistingBook(found)
      return
    }
    setExistingBook(null)
    void autofill(cleaned)
  }

  const onDetect = useCallback((raw: string) => {
    void handleIsbn(cleanIsbn(raw))
  }, [])

  async function onSaveScan() {
    if (!existingBook) return
    const clean = cleanIsbn(isbn)
    if (!clean) return
    setScanSaving(true)
    setError(null)
    try {
      const created = await createScan({
        id_article_livre: existingBook.id_article,
        isbn_lu: clean,
        valide: false,
      })
      setScanSaved(`Scan enregistré (#${created.id_scan_isbn}).`)
    } catch (e) {
      const err = e as unknown
      setError(err instanceof ApiError ? err.message : 'Enregistrement du scan impossible')
    } finally {
      setScanSaving(false)
    }
  }
  const {
    start: startScanner,
    stop: stopScanner,
    running: scanning,
    error: scanError,
    setError: setScanError,
  } = useBarcodeScanner(videoRef, onDetect, {
    cameraErrorMessage: 'Impossible d’accéder à la caméra',
    videoUnavailableMessage: 'Caméra introuvable',
  })

  async function onAutofill() {
    await handleIsbn(cleanIsbn(isbn))
  }

  async function onFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    if (!f) return
    setScanError(null)

    // The photo may happen to frame the back-cover barcode -- try reading an
    // ISBN off it first, purely as a convenience (triggers the usual
    // OpenLibrary autofill). Either way, the button's real purpose is below:
    // use the picture itself as the book's cover, since OpenLibrary often has
    // no cover art, or the lookup fails outright.
    try {
      const bitmap = await createImageBitmap(f)
      if (typeof window.BarcodeDetector !== 'undefined') {
        const detector = new BarcodeDetector({ formats: ['ean_13', 'ean_8', 'qr_code'] })
        const results = await detector.detect(bitmap)
        const code = results?.[0]?.rawValue
        if (code) void handleIsbn(cleanIsbn(code))
      }
    } catch {
      // not decodable as a barcode photo -- fine, still used as the cover below
    }

    setPhotoUploading(true)
    try {
      const uploaded = await uploadLocalImage(f)
      setImageLink(uploaded)
    } catch {
      setScanError('Impossible d\u2019envoyer la photo')
    } finally {
      setPhotoUploading(false)
    }
  }

  useEffect(() => {
    async function loadLists() {
      try {
        setEtatList(await listCatalog<EtatItem>('etat-usures'))
      } catch {
        // ignore
      }
      try {
        const typesArr = await listCatalog<TypeObjetItem>('type-objets')
        setTypeList(typesArr)
        // default TypeObjet to 'Livre' when available
        const def = typesArr.find((t) => t.code === 'BOOK' || (t.libelle || '').toLowerCase() === 'livre')
        if (def && !idType) setIdType(String(def.id_type_objet))
      } catch {
        // ignore
      }
      try {
        const sourcesArr = await listSources()
        setSourceList(sourcesArr)
        // Pre-select the last (most recently added) source, per the volunteer
        // workflow: new stock keeps arriving from whichever source was set up
        // most recently, so that's the one most likely to be the right pick.
        const lastSource = sourcesArr[sourcesArr.length - 1]
        if (lastSource && !idSource) setIdSource(String(lastSource.id_source_stock))
      } catch {
        // ignore
      }
    }
    void loadLists()
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const param = new URLSearchParams(window.location.search).get('isbn')
    const raw = (param || '').trim()
    if (!raw) return

    void handleIsbn(cleanIsbn(raw))
    // run once on mount
  }, [])

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setInvalidFields(new Set())
    setLoading(true)
    try {
      // simple client-side validation: all fields required (description optional)
      if (!titre.trim() || !isbn.trim() || !auteur.trim() || !prix.trim() || !idEtat || !idType) {
        const missing = new Set<string>()
        if (!titre.trim()) missing.add('titre')
        if (!isbn.trim()) missing.add('isbn')
        if (!auteur.trim()) missing.add('auteur')
        if (!prix.trim()) missing.add('prix')
        if (!idEtat) missing.add('etat')
        if (!idType) missing.add('type')
        setInvalidFields(missing)
        setError('Veuillez remplir tous les champs obligatoires.')
        setLoading(false)
        return
      }
      const prixNum = Number(prix)
      if (!Number.isFinite(prixNum) || prixNum < 0) {
        setInvalidFields(new Set(['prix']))
        setError("Le prix n'est pas valide")
        setLoading(false)
        return
      }
      // If admin provided an external image URL, ask backend to fetch it first
      let finalImage = imageLink || null
      if (finalImage && isExternalImage(finalImage)) {
        try {
          finalImage = await fetchRemoteImage(finalImage)
        } catch {
          // ignore fetch errors; backend will try to download on create
        }
      }
      const createdBook = await createBook({
        id_type_objet: Number(idType),
        id_etat_usure: Number(idEtat),
        titre,
        isbn,
        auteur: auteur || null,
        editeur: null,
        date_publication: null,
        langue: null,
        description: description || null,
        image_link: finalImage || null,
        prix_chf: prixNum,
        actif: true,
        id_source_stock: idSource ? Number(idSource) : undefined,
      })
      setCreated(createdBook)
    } catch (e) {
      const err = e as unknown
      setError(err instanceof ApiError ? err.message : 'Création impossible')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container page-main">
      <div className="content-center">
        <h1 style={{ margin: 0 }}>Ajouter un livre</h1>

        {created ? (
          <div className="card cardPadding" style={{ display: 'grid', gap: 12 }}>
            <div className="banner-success" role="status" aria-live="polite">Livre ajouté au catalogue.</div>
            <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
              {created.image_link ? (
                <Image
                  src={created.image_link}
                  alt={created.titre}
                  width={64}
                  height={88}
                  style={{ objectFit: 'cover', borderRadius: 10, border: '1px solid var(--color-border)' }}
                  unoptimized={isExternalImage(created.image_link)}
                />
              ) : (
                <div className="card" style={{ width: 64, height: 88 }} />
              )}
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 900 }}>{created.titre}</div>
                <div className="muted">ISBN: {created.isbn}</div>
                <div className="muted">Prix: CHF {created.prix_chf.toFixed(2)}</div>
              </div>
              <Link className="btn" href={`/admin/books/${created.id_article}`} aria-label={`Voir la fiche du livre ${created.titre}`}>
                Voir la fiche
              </Link>
            </div>
            <button className="btn btnPrimary" type="button" onClick={resetForm}>
              Ajouter un nouveau livre
            </button>
          </div>
        ) : existingBook ? (
          <div className="card cardPadding" style={{ display: 'grid', gap: 12 }}>
            <div className="muted">Ce livre est déjà au catalogue — inutile de le recréer.</div>
            <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
              {existingBook.image_link ? (
                <Image
                  src={existingBook.image_link}
                  alt={existingBook.titre}
                  width={64}
                  height={88}
                  style={{ objectFit: 'cover', borderRadius: 10, border: '1px solid var(--color-border)' }}
                  unoptimized={isExternalImage(existingBook.image_link)}
                />
              ) : (
                <div className="card" style={{ width: 64, height: 88 }} />
              )}
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 900 }}>{existingBook.titre}</div>
                <div className="muted">ISBN: {existingBook.isbn}</div>
                <div className="muted">Prix: CHF {existingBook.prix_chf.toFixed(2)}</div>
              </div>
              <Link className="btn" href={`/admin/books/${existingBook.id_article}`} aria-label={`Voir les détails du livre ${existingBook.titre}`}>
                Détails
              </Link>
            </div>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
              <button className="btn btnPrimary" type="button" onClick={onSaveScan} disabled={scanSaving}>
                {scanSaving ? 'Enregistrement…' : 'Enregistrer le scan'}
              </button>
              <button
                className="btn"
                type="button"
                onClick={() => {
                  setExistingBook(null)
                  setIsbn('')
                  setScanSaved(null)
                }}
              >
                Ajouter un autre livre
              </button>
            </div>
            {scanSaved ? <div className="banner-success" role="status" aria-live="polite">{scanSaved}</div> : null}
            {error ? <div className="banner-error" role="alert">{error}</div> : null}
          </div>
        ) : (
        <form className="card cardPadding" onSubmit={onSubmit}>
          <div className="form-row">
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <button className="btn" type="button" onClick={() => void startScanner()}>
                Scanner un code-barres
              </button>
              <label className="btn" style={{ cursor: 'pointer' }}>
                {photoUploading ? 'Envoi…' : 'Photographier le livre'}
                <input
                  type="file"
                  accept="image/*"
                  capture="environment"
                  onChange={onFileUpload}
                  disabled={photoUploading}
                  style={{ display: 'none' }}
                />
              </label>
            </div>
            {/* Fallback for when OpenLibrary has no cover art (or the ISBN
                lookup fails outright): opens the device's rear camera so the
                admin can photograph the book itself and use that as its image. */}
            {scanError ? <div className="banner-error" role="alert">{scanError}</div> : null}
          </div>

          <div style={{ display: 'grid', gap: 6 }}>
            <label htmlFor="new-book-titre" style={{ fontWeight: 700 }}>Nom</label>
            <input
              id="new-book-titre"
              className="input"
              value={titre}
              onChange={(e) => { setTitre(e.target.value); if (invalidFields.has('titre')) setInvalidFields((s) => { const n = new Set(s); n.delete('titre'); return n }) }}
              placeholder="Titre"
              required
              aria-invalid={invalidFields.has('titre')}
              aria-describedby={invalidFields.has('titre') ? 'new-book-form-error' : undefined}
            />
          </div>

          <div className="form-row">
            <div style={{ display: 'grid', gap: 6 }}>
              <label htmlFor="new-book-isbn" style={{ fontWeight: 700 }}>ISBN</label>
              <input
                id="new-book-isbn"
                className="input"
                value={isbn}
                onChange={(e) => { setIsbn(e.target.value); if (invalidFields.has('isbn')) setInvalidFields((s) => { const n = new Set(s); n.delete('isbn'); return n }) }}
                placeholder="ISBN"
                required
                aria-invalid={invalidFields.has('isbn')}
                aria-describedby={invalidFields.has('isbn') ? 'new-book-form-error' : undefined}
              />
            </div>
            <button className="btn" type="button" onClick={onAutofill} disabled={autofillLoading}>
              {autofillLoading ? 'Recherche…' : 'OpenLibrary'}
            </button>
          </div>

          <div className="two-up">
            <div>
              {/* This page only ever creates a Livre (see createBook below), so
                  the type is locked to "Livre" rather than offered as a free
                  choice — picking e.g. "DVD" here would silently create a book
                  row typed as something else. `idType` still resolves to the
                  right id (see loadLists/defaultTypeId), it's just not editable. */}
              <label htmlFor="new-book-type" className="sr-only">Type d&apos;objet</label>
              <select id="new-book-type" className="input" value={idType} disabled required>
                <option value={idType}>
                  {typeList.find((t) => String(t.id_type_objet) === idType)?.libelle || 'Livre'}
                </option>
              </select>
            </div>

            <div>
              <label htmlFor="new-book-etat" className="sr-only">État du livre</label>
              <select
                id="new-book-etat"
                className="input"
                value={idEtat}
                onChange={(e) => { setIdEtat(e.target.value); if (invalidFields.has('etat')) setInvalidFields((s) => { const n = new Set(s); n.delete('etat'); return n }) }}
                required
                aria-invalid={invalidFields.has('etat')}
                aria-describedby={invalidFields.has('etat') ? 'new-book-form-error' : undefined}
              >
                <option value="">État</option>
                {etatList.map((e) => (
                  <option key={e.id_etat_usure} value={String(e.id_etat_usure)}>
                    {e.libelle}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gap: 6 }}>
            <label htmlFor="new-book-source" style={{ fontWeight: 700 }}>Source de stock</label>
            <select id="new-book-source" className="input" value={idSource} onChange={(e) => setIdSource(e.target.value)}>
              <option value="">Source par défaut du serveur</option>
              {sourceList.map((s) => (
                <option key={s.id_source_stock} value={String(s.id_source_stock)}>
                  {s.libelle}
                </option>
              ))}
            </select>
          </div>

          <div style={{ display: 'grid', gap: 6 }}>
            <label htmlFor="new-book-auteur" style={{ fontWeight: 700 }}>Auteur</label>
            <input
              id="new-book-auteur"
              className="input"
              value={auteur}
              onChange={(e) => { setAuteur(e.target.value); if (invalidFields.has('auteur')) setInvalidFields((s) => { const n = new Set(s); n.delete('auteur'); return n }) }}
              placeholder="Auteur"
              required
              aria-invalid={invalidFields.has('auteur')}
              aria-describedby={invalidFields.has('auteur') ? 'new-book-form-error' : undefined}
            />
          </div>

          <div style={{ display: 'grid', gap: 6 }}>
            <label htmlFor="new-book-prix" style={{ fontWeight: 700 }}>Prix (CHF)</label>
            <input
              id="new-book-prix"
              className="input"
              value={prix}
              onChange={(e) => { setPrix(e.target.value); if (invalidFields.has('prix')) setInvalidFields((s) => { const n = new Set(s); n.delete('prix'); return n }) }}
              placeholder="Prix CHF"
              required
              aria-invalid={invalidFields.has('prix')}
              aria-describedby={invalidFields.has('prix') ? 'new-book-form-error' : undefined}
            />
          </div>

          <div style={{ display: 'grid', gap: 6 }}>
            <label htmlFor="new-book-image" style={{ fontWeight: 700 }}>Image URL</label>
            <input
              id="new-book-image"
              className="input"
              value={imageLink}
              onChange={(e) => setImageLink(e.target.value)}
              placeholder="https://… ou laissez vide si pas d'image"
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {imageLink ? (
              <Image
                src={imageLink}
                alt="Aperçu"
                width={80}
                height={110}
                style={{ objectFit: 'cover', borderRadius: 8, border: '1px solid var(--color-border)' }}
                unoptimized={isExternalImage(imageLink)}
              />
            ) : (
              <div
                className="book-image-wrap"
                style={{ width: 80, height: 110, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              >
                <span style={{ fontSize: 24 }}>📖</span>
              </div>
            )}
          </div>

          <div style={{ display: 'grid', gap: 6 }}>
            <label htmlFor="new-book-description" style={{ fontWeight: 700 }}>Description</label>
            <textarea
              id="new-book-description"
              className="card"
              style={{ borderRadius: 14, padding: 12, borderColor: 'var(--color-border)', minHeight: 120 }}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Description (optionnel)"
            />
          </div>
          {error ? <div id="new-book-form-error" className="banner-error" role="alert">{error}</div> : null}
          <button className="btn btnPrimary" type="submit" disabled={loading}>
            {loading ? 'Création…' : 'Créer'}
          </button>
        </form>
        )}

        {scanning ? (
          <div className="modal" role="dialog" aria-modal="true" aria-labelledby="scanner-dialog-title">
            <div className="modal-dialog">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong id="scanner-dialog-title">Scanner ISBN</strong>
                <button className="btn" onClick={stopScanner} aria-label="Fermer le scanner de code-barres">
                  Fermer
                </button>
              </div>
              <div style={{ marginTop: 8 }}>
                <video ref={videoRef} style={{ width: '100%', borderRadius: 8 }} />
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}
