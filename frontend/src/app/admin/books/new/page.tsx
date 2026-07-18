'use client'

import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { ApiError, apiFetch } from '@/services/api'
import { createBook } from '@/services/books'
import Image from 'next/image'
import { lookupIsbn } from '@/services/openlibrary'
import { fetchRemoteImage } from '@/services/images'
import { cleanIsbn } from '@/lib/isbn'
import { isExternalImage } from '@/lib/images'

export default function AdminNewBookPage() {
  const router = useRouter()
  const [titre, setTitre] = useState('')
  const [isbn, setIsbn] = useState('')
  const [auteur, setAuteur] = useState('')
  const [prix, setPrix] = useState('')
  const [idEtat, setIdEtat] = useState('')
  const [idType, setIdType] = useState('')
  const [etatList, setEtatList] = useState<any[]>([])
  const [typeList, setTypeList] = useState<any[]>([])
  const [imageLink, setImageLink] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [autofillLoading, setAutofillLoading] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [scanError, setScanError] = useState<string | null>(null)
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const intervalRef = useRef<number | null>(null)
  const lastRawRef = useRef<string>('')
  const lastAtRef = useRef<number>(0)

  async function startScanner() {
    setScanError(null)
    try {
      // stop any existing stream first
      stopScanner()

      const stream = await (navigator.mediaDevices as any).getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
      })

      streamRef.current = stream

      // ensure modal/video DOM is present
      setScanning(true)

      // wait for video element to be mounted
      for (let i = 0; i < 20 && !videoRef.current; i++) {
        // eslint-disable-next-line no-await-in-loop
        await new Promise((r) => setTimeout(r, 100))
      }
      const v = videoRef.current
      if (!v) {
        setScanError('Caméra introuvable')
        return
      }
      v.autoplay = true
      v.playsInline = true
      v.srcObject = stream
      await v.play()

      const hasDetector = typeof (window as any).BarcodeDetector !== 'undefined'
      if (hasDetector) {
        const formats: BarcodeFormat[] = ['ean_13', 'ean_8', 'upc_a', 'upc_e', 'code_128']
        const detector: any = new (window as any).BarcodeDetector({ formats })

        intervalRef.current = window.setInterval(async () => {
          const vv = videoRef.current
          if (!vv || vv.readyState < 2) return
          try {
            const codes = await detector.detect(vv)
            if (!codes || !codes.length) return
            const raw = (codes[0]?.rawValue || '').trim()
            if (!raw) return

            const now = Date.now()
            if (raw === lastRawRef.current && now - lastAtRef.current < 1500) return
            lastRawRef.current = raw
            lastAtRef.current = now

            // found
            const cleaned = cleanIsbn(raw)
            stopScanner()
            setIsbn(cleaned)
            await autofill(cleaned)
            return
          } catch (err) {
            // ignore transient detection errors
          }
        }, 350)
      }
    } catch (e) {
      setScanError('Impossible d\u2019acc\u00E9der \u00E0 la cam\u00E9ra')
      setScanning(false)
    }
  }

  function stopScanner() {
    setScanning(false)
    try {
      if (intervalRef.current) {
        window.clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      const v = videoRef.current
      if (v && v.srcObject) {
        const tracks = (v.srcObject as MediaStream).getTracks()
        tracks.forEach((t) => t.stop())
        v.srcObject = null
      }
      if (streamRef.current) {
        try {
          for (const t of streamRef.current.getTracks()) t.stop()
        } catch {
          // ignore
        }
        streamRef.current = null
      }
    } catch (e) {
      // ignore
    }
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
      const detector: any = (window as any).BarcodeDetector ? new (window as any).BarcodeDetector({ formats: ['ean_13', 'ean_8', 'qr_code'] }) : null
      if (detector) {
        const results = await detector.detect(bitmap as any)
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
    return () => {
      stopScanner()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    async function loadLists() {
      try {
        const etats = await apiFetch('/catalog/etat-usures')
        setEtatList(etats as any[])
      } catch {
        // ignore
      }
      try {
        const types = await apiFetch('/catalog/type-objets')
        const typesArr = Array.isArray(types) ? types : []
        setTypeList(typesArr as any[])
        // default TypeObjet to 'Livre' when available
        const def = typesArr.find((t: any) => t.code === 'BOOK' || ((t.libelle || '') as string).toLowerCase() === 'livre')
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
