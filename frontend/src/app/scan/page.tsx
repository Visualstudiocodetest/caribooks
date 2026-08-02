'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { ApiError } from '@/services/api'
import { getBookByIsbn } from '@/services/books'
import { createScan } from '@/services/scans'
import { useAuth } from '@/components/auth/AuthProvider'
import type { BookRead } from '@/types/api'
import { lookupIsbn } from '@/services/openlibrary'
import { fetchRemoteImage } from '@/services/images'
import { cleanIsbn } from '@/lib/isbn'
import { isExternalImage } from '@/lib/images'
import { useBarcodeScanner } from '@/hooks/useBarcodeScanner'

type OpenLibraryPreview = {
  titre: string
  auteur: string
  image_link: string | null
  description: string
}

function isbn13To10(isbn13: string): string | null {
  const s = cleanIsbn(isbn13)
  if (s.length !== 13) return null
  if (!s.startsWith('978')) return null
  const core = s.slice(3, 12) // 9 digits
  if (!/^\d{9}$/.test(core)) return null
  let sum = 0
  for (let i = 0; i < 9; i++) sum += (10 - i) * Number(core[i])
  const mod = 11 - (sum % 11)
  const check = mod === 10 ? 'X' : mod === 11 ? '0' : String(mod)
  return `${core}${check}`
}

export default function ScanPage() {
  const { isLoggedIn, isAdmin } = useAuth()
  const videoRef = useRef<HTMLVideoElement | null>(null)

  const [isbn, setIsbn] = useState('')
  const [book, setBook] = useState<BookRead | null>(null)
  const [openPreview, setOpenPreview] = useState<OpenLibraryPreview | null>(null)
  const [lookupLoading, setLookupLoading] = useState(false)
  const [saveLoading, setSaveLoading] = useState(false)
  const [success, setSuccess] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const onDetect = useCallback((raw: string) => setIsbn(cleanIsbn(raw)), [])
  const { start: startCamera, stop: stopCamera, running, error: cameraError, hasBarcodeDetector } = useBarcodeScanner(videoRef, onDetect)

  async function toggleCamera() {
    setError(null)
    setSuccess(null)
    if (running) {
      stopCamera()
    } else {
      await startCamera()
    }
  }

  async function lookup(isbnValue: string) {
    const clean = cleanIsbn(isbnValue)
    if (!clean) return

    setLookupLoading(true)
    setBook(null)
    setOpenPreview(null)
    setError(null)
    setSuccess(null)

    const candidates = [clean]
    const maybe10 = isbn13To10(clean)
    if (maybe10 && maybe10 !== clean) candidates.push(maybe10)

    try {
      for (const c of candidates) {
        const found = await getBookByIsbn(c)
        if (found) {
          setBook(found)
          return
        }
      }

      // Not in DB: try OpenLibrary to prefill a potential creation form.
      for (const c of candidates) {
        try {
          const data = await lookupIsbn(c)
          if (!data) continue

          const titre = [data.title, data.subtitle].filter(Boolean).join(' — ') || c
          const auteur = data.authors?.map((a) => a.name).filter(Boolean).join(', ') || ''
          let image_link = data.cover?.large || data.cover?.medium || data.cover?.small || null
          const description = typeof data.notes === 'string' ? data.notes : ''

          if (image_link) {
            try {
              // ask backend to download and serve the image locally
              image_link = await fetchRemoteImage(image_link)
            } catch {
              // ignore failures and fall back to remote URL
            }
          }

          setOpenPreview({ titre, auteur, image_link, description })
          setSuccess('Livre non présent dans la base. Données OpenLibrary chargées pour pré-remplir.')
          return
        } catch {
          // ignore OpenLibrary errors; fall back to generic message
        }
      }

      setError('Livre introuvable dans la base Caribooks pour cet ISBN.')
    } catch (e) {
      const err = e as unknown
      setError(err instanceof ApiError ? err.message : 'Recherche impossible')
    } finally {
      setLookupLoading(false)
    }
  }

  async function onSaveScan() {
    setError(null)
    setSuccess(null)

    if (!isLoggedIn) {
      setError('Connectez-vous pour enregistrer un scan.')
      return
    }
    if (!book) {
      setError('Aucun livre sélectionné.')
      return
    }

    const clean = cleanIsbn(isbn)
    if (!clean) {
      setError('ISBN invalide.')
      return
    }

    setSaveLoading(true)
    try {
      const created = await createScan({
        id_article_livre: book.id_article,
        isbn_lu: clean,
        valide: false,
      })
      setSuccess(`Scan enregistré (#${created.id_scan_isbn}).`)
    } catch (e) {
      const err = e as unknown
      setError(err instanceof ApiError ? err.message : 'Enregistrement impossible')
    } finally {
      setSaveLoading(false)
    }
  }

  useEffect(() => {
    if (!isbn) return
    void lookup(isbn)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isbn])

  return (
    <div className="content-center">
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 10 }}>
        <h1 style={{ margin: 0 }}>Scanner un ISBN</h1>
        {isLoggedIn ? (
          <span className="muted">Connecté</span>
        ) : (
          <Link className="btn btnPrimary" href="/login">
            Connexion
          </Link>
        )}
      </div>

      <div className="card cardPadding">
        <div className="form-row two">
          <input
            className="input"
            value={isbn}
            onChange={(e) => setIsbn(e.target.value)}
            placeholder={lookupLoading ? 'Recherche…' : 'ISBN (manuel ou scanné)'}
            inputMode="numeric"
          />
          <button className="btn btnPrimary" type="button" onClick={toggleCamera}>
            {running ? 'Stop' : 'Caméra'}
          </button>
        </div>

        <div className="muted">
          {hasBarcodeDetector
            ? "Sur mobile, pointez la caméra vers le code-barres (EAN-13)."
            : "Votre navigateur ne supporte pas BarcodeDetector. Utilisez la saisie manuelle."}
        </div>
        <div className="video-preview card">
          <video
            ref={videoRef}
            playsInline
            muted
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              opacity: running ? 1 : 0,
            }}
          />
          {!running ? <div className="video-overlay">Aperçu caméra</div> : null}
        </div>
      </div>

      {book ? (
        <div className="card cardPadding">
          <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
            {book.image_link ? (
              <Image
                src={book.image_link}
                alt={book.titre}
                width={64}
                height={88}
                style={{ objectFit: 'cover', borderRadius: 10, border: '1px solid var(--color-border)' }}
                unoptimized={isExternalImage(book.image_link)}
              />
            ) : (
              <div className="card" style={{ width: 64, height: 88 }} />
            )}
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 900 }}>{book.titre}</div>
              <div className="muted">ISBN: {book.isbn}</div>
              <div className="muted">Prix: CHF {book.prix_chf.toFixed(2)}</div>
            </div>
            <Link className="btn" href={`/books/${book.id_article}`}>
              Détails
            </Link>
          </div>

          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <button className="btn btnPrimary" type="button" onClick={onSaveScan} disabled={saveLoading}>
              {saveLoading ? 'Enregistrement…' : 'Enregistrer le scan'}
            </button>
            <button
              className="btn"
              type="button"
              onClick={() => {
                setIsbn('')
                setBook(null)
                setError(null)
                setSuccess(null)
              }}
            >
              Nouveau scan
            </button>
          </div>
        </div>
      ) : null}

      {!book && openPreview ? (
        <div className="card cardPadding">
          <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
            {openPreview.image_link ? (
              <Image
                src={openPreview.image_link}
                alt={openPreview.titre}
                width={64}
                height={88}
                style={{ objectFit: 'cover', borderRadius: 10, border: '1px solid var(--color-border)' }}
                unoptimized={isExternalImage(openPreview.image_link)}
              />
            ) : (
              <div className="card" style={{ width: 64, height: 88 }} />
            )}
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 900 }}>{openPreview.titre}</div>
              <div className="muted">{openPreview.auteur ? `Auteur: ${openPreview.auteur}` : 'Auteur: —'}</div>
              <div className="muted">ISBN: {cleanIsbn(isbn)}</div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {isAdmin ? (
              <Link className="btn btnPrimary" href={`/admin/books/new?isbn=${encodeURIComponent(cleanIsbn(isbn))}`}>
                Pré-remplir le formulaire (admin)
              </Link>
            ) : (
              <div className="muted">Demandez à un admin d’ajouter ce livre au catalogue.</div>
            )}
          </div>
        </div>
      ) : null}

      {success ? <div className="banner-success">{success}</div> : null}
      {error || cameraError ? <div className="banner-error">{error || cameraError}</div> : null}
    </div>
  )
}
