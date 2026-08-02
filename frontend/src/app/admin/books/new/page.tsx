'use client'

import { useEffect, useState, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { ApiError } from '@/services/api'
import { createBook } from '@/services/books'
import { listCatalog } from '@/services/catalog'
import Image from 'next/image'
import { lookupIsbn } from '@/services/openlibrary'
import { fetchRemoteImage } from '@/services/images'
import { cleanIsbn } from '@/lib/isbn'
import { isExternalImage } from '@/lib/images'
import { useBarcodeScanner } from '@/hooks/useBarcodeScanner'

type EtatItem = { id_etat_usure: number; libelle: string }
type TypeObjetItem = { id_type_objet: number; libelle: string; code?: string }

export default function AdminNewBookPage() {
  const router = useRouter()
  const [titre, setTitre] = useState('')
  const [isbn, setIsbn] = useState('')
  const [auteur, setAuteur] = useState('')
  const [prix, setPrix] = useState('')
  const [idEtat, setIdEtat] = useState('')
  const [idType, setIdType] = useState('')
  const [etatList, setEtatList] = useState<EtatItem[]>([])
  const [typeList, setTypeList] = useState<TypeObjetItem[]>([])
  const [imageLink, setImageLink] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [autofillLoading, setAutofillLoading] = useState(false)
  const videoRef = useRef<HTMLVideoElement | null>(null)

  const onDetect = useCallback((raw: string) => {
    const cleaned = cleanIsbn(raw)
    setIsbn(cleaned)
    void autofill(cleaned)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
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
      const cover = data.cover?.large || data.cover?.medium || data.cover?.small
      if (cover) {
        try {
          const served = await fetchRemoteImage(cover)
          setImageLink(served)
        } catch {
          setImageLink(cover)
        }
      }
      const desc = typeof data.notes === 'string' ? data.notes : ''
      if (desc) setDescription(desc)
    } catch {
      setError('Impossible de contacter OpenLibrary.')
    } finally {
      setAutofillLoading(false)
    }
  }

  async function onAutofill() {
    await autofill(isbn)
  }

  async function onFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    if (!f) return
    setScanError(null)
    try {
      const bitmap = await createImageBitmap(f)
      const detector = typeof window.BarcodeDetector !== 'undefined'
        ? new BarcodeDetector({ formats: ['ean_13', 'ean_8', 'qr_code'] })
        : null
      if (detector) {
        const results = await detector.detect(bitmap)
        if (results && results.length) {
          const code = results[0].rawValue
          if (code) {
            const cleaned = cleanIsbn(code)
            setIsbn(cleaned)
            await autofill(cleaned)
            return
          }
        }
      }
      setScanError('Aucun code détecté dans l\u2019image')
    } catch (err) {
      setScanError('Impossible de traiter l\u2019image')
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
    }
    void loadLists()
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const param = new URLSearchParams(window.location.search).get('isbn')
    const raw = (param || '').trim()
    if (!raw) return

    setIsbn(raw)
    void autofill(raw)
    // run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      // simple client-side validation: all fields required (description optional)
      if (!titre.trim() || !isbn.trim() || !auteur.trim() || !prix.trim() || !idEtat || !idType) {
        setError('Veuillez remplir tous les champs obligatoires.')
        setLoading(false)
        return
      }
      const prixNum = Number(prix)
      if (!Number.isFinite(prixNum) || prixNum < 0) {
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
      const created = await createBook({
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
      })
      router.push(`/admin/books/${created.id_article}`)
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
        <h1 style={{ margin: 0 }}>Nouveau livre</h1>

        <form className="card cardPadding" onSubmit={onSubmit}>
          <div className="form-row">
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <button className="btn" type="button" onClick={() => void startScanner()}>
                Quick scanner
              </button>
              <label className="btn" style={{ cursor: 'pointer' }}>
                Upload image
                <input type="file" accept="image/*" onChange={onFileUpload} style={{ display: 'none' }} />
              </label>
            </div>
            {scanError ? <div className="banner-error">{scanError}</div> : null}
          </div>

          <div style={{ display: 'grid', gap: 6 }}>
            <label style={{ fontWeight: 700 }}>Nom</label>
            <input className="input" value={titre} onChange={(e) => setTitre(e.target.value)} placeholder="Titre" required />
          </div>

          <div className="form-row">
            <div style={{ display: 'grid', gap: 6 }}>
              <label style={{ fontWeight: 700 }}>ISBN</label>
              <input className="input" value={isbn} onChange={(e) => setIsbn(e.target.value)} placeholder="ISBN" required />
            </div>
            <button className="btn" type="button" onClick={onAutofill} disabled={autofillLoading}>
              {autofillLoading ? 'Recherche…' : 'OpenLibrary'}
            </button>
          </div>

          <div className="two-up">
            <select className="input" value={idType} onChange={(e) => setIdType(e.target.value)} required>
              <option value="">Type d'objet...</option>
              {typeList.map((t) => (
                <option key={t.id_type_objet} value={String(t.id_type_objet)}>
                  {t.libelle}
                </option>
              ))}
            </select>

            <select className="input" value={idEtat} onChange={(e) => setIdEtat(e.target.value)} required>
              <option value="">État</option>
              {etatList.map((e) => (
                <option key={e.id_etat_usure} value={String(e.id_etat_usure)}>
                  {e.libelle}
                </option>
              ))}
            </select>
          </div>

          <div style={{ display: 'grid', gap: 6 }}>
            <label style={{ fontWeight: 700 }}>Auteur</label>
            <input className="input" value={auteur} onChange={(e) => setAuteur(e.target.value)} placeholder="Auteur" required />
          </div>

          <div style={{ display: 'grid', gap: 6 }}>
            <label style={{ fontWeight: 700 }}>Prix (CHF)</label>
            <input className="input" value={prix} onChange={(e) => setPrix(e.target.value)} placeholder="Prix CHF" required />
          </div>

          <div style={{ display: 'grid', gap: 6 }}>
            <label style={{ fontWeight: 700 }}>Image URL</label>
            <input
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
            <label style={{ fontWeight: 700 }}>Description</label>
            <textarea
              className="card"
              style={{ borderRadius: 14, padding: 12, borderColor: 'var(--color-border)', minHeight: 120 }}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Description (optionnel)"
            />
          </div>
          {error ? <div className="banner-error">{error}</div> : null}
          <button className="btn btnPrimary" type="submit" disabled={loading}>
            {loading ? 'Création…' : 'Créer'}
          </button>
        </form>

        {scanning ? (
          <div className="modal">
            <div className="modal-dialog">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong>Scanner ISBN</strong>
                <button className="btn" onClick={stopScanner}>
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
