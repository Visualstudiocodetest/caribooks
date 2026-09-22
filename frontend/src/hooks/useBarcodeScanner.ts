'use client'

import { useCallback, useEffect, useRef, useState, type RefObject } from 'react'

// A book's ISBN barcode is always an EAN-13 (Bookland, 978/979). The list used
// to include upc_a/upc_e/code_128 as well, which only widened the ways a scan
// could pick up the WRONG barcode -- second-hand books routinely carry a shop
// price sticker or a library label alongside the ISBN, and those decode as
// UPC-A/Code 128. ean_8 stays off for the same reason. isValidIsbn (lib/isbn)
// is the second line of defence for a misread or a non-Bookland EAN-13.
const DEFAULT_FORMATS: BarcodeFormat[] = ['ean_13']
const DEDUPE_WINDOW_MS = 1500
const DETECT_INTERVAL_MS = 350
const VIDEO_MOUNT_RETRIES = 20
const VIDEO_MOUNT_RETRY_DELAY_MS = 100

export interface UseBarcodeScannerOptions {
  formats?: BarcodeFormat[]
  cameraUnavailableMessage?: string
  cameraErrorMessage?: string
  videoUnavailableMessage?: string
  detectorUnavailableMessage?: string
  /** Reject a decoded value and keep scanning (e.g. a shop price sticker that
   *  is not an ISBN). Omitted, every decoded barcode is accepted. */
  accept?: (raw: string) => boolean
}

/**
 * Drives a live camera preview + BarcodeDetector polling loop. Shared by the
 * public scan page and the admin "new book" quick-scan modal, which previously
 * each hand-rolled the same getUserMedia/detect-interval/dedupe logic.
 *
 * `videoRef` may point at a <video> that mounts only after `start()` sets
 * `running` true (e.g. inside a conditionally-rendered modal) — start() waits
 * briefly for it to appear, which is a no-op when the element is already mounted.
 */
export function useBarcodeScanner(
  videoRef: RefObject<HTMLVideoElement | null>,
  onDetect: (raw: string) => void,
  options: UseBarcodeScannerOptions = {},
) {
  const {
    formats = DEFAULT_FORMATS,
    cameraUnavailableMessage = 'Caméra indisponible. Utilisez la saisie manuelle d’ISBN.',
    cameraErrorMessage = 'Accès caméra refusé ou impossible. Vérifiez les permissions du navigateur.',
    videoUnavailableMessage = 'Aperçu vidéo indisponible.',
    detectorUnavailableMessage = 'La lecture automatique de code-barres n’est pas prise en charge par ce navigateur (Safari, Firefox). Saisissez l’ISBN à la main.',
    accept,
  } = options

  const streamRef = useRef<MediaStream | null>(null)
  const intervalRef = useRef<number | null>(null)
  const lastRawRef = useRef<string>('')
  const lastAtRef = useRef<number>(0)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const hasBarcodeDetector = typeof window !== 'undefined' && typeof window.BarcodeDetector !== 'undefined'

  const stop = useCallback(() => {
    if (intervalRef.current) {
      window.clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    if (streamRef.current) {
      for (const t of streamRef.current.getTracks()) t.stop()
      streamRef.current = null
    }
    const video = videoRef.current
    if (video) {
      try {
        video.pause()
      } catch {
        // ignore
      }
      video.srcObject = null
    }
    setRunning(false)
  }, [videoRef])

  const start = useCallback(async () => {
    setError(null)
    stop()

    if (typeof window === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      setError(cameraUnavailableMessage)
      return
    }

    // Without BarcodeDetector (Safari incl. every iOS browser, and Firefox)
    // the old code still started the camera and then simply never scheduled a
    // detection loop: the user got a live preview that silently never
    // recognised anything, with no indication why. Say so instead of opening a
    // camera that cannot do the job.
    if (!hasBarcodeDetector) {
      setError(detectorUnavailableMessage)
      return
    }

    // Set before requesting the stream so a conditionally-rendered <video> mounts.
    setRunning(true)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      })
      streamRef.current = stream

      let video = videoRef.current
      for (let i = 0; i < VIDEO_MOUNT_RETRIES && !video; i++) {
        await new Promise((r) => setTimeout(r, VIDEO_MOUNT_RETRY_DELAY_MS))
        video = videoRef.current
      }
      if (!video) {
        setError(videoUnavailableMessage)
        stop()
        return
      }
      video.srcObject = stream
      // iOS Safari refuses to play an inline video without BOTH of these and
      // rejects play() ("NotAllowedError"), which the catch below reported as
      // "Accès caméra refusé" -- so on iPhone the scanner looked like a denied
      // camera permission no matter how many times the user granted it. The
      // <video> element's own attributes are set by the caller too; setting
      // them on the object here makes the hook work regardless of that.
      video.muted = true
      video.setAttribute('playsinline', 'true')
      video.setAttribute('muted', 'true')
      await video.play()

      {
        const detector = new BarcodeDetector({ formats })

        intervalRef.current = window.setInterval(async () => {
          const v = videoRef.current
          if (!v || v.readyState < 2) return
          try {
            const codes = await detector.detect(v)
            if (!codes.length) return
            // Consider EVERY barcode in frame, not just codes[0]. A book held
            // up to the camera often shows its ISBN next to a price or library
            // sticker, and which one lands first is arbitrary -- taking codes[0]
            // blindly meant a scan could lock onto the wrong number. `accept`
            // (isValidIsbn at the call site) picks the real one; if none of
            // them qualifies, keep scanning rather than stopping on a bad read.
            const values = codes.map((c) => (c.rawValue || '').trim()).filter(Boolean)
            const raw = accept ? values.find((v2) => accept(v2)) : values[0]
            if (!raw) return

            const now = Date.now()
            if (raw === lastRawRef.current && now - lastAtRef.current < DEDUPE_WINDOW_MS) return
            lastRawRef.current = raw
            lastAtRef.current = now

            stop()
            onDetect(raw)
          } catch {
            // ignore transient detection errors
          }
        }, DETECT_INTERVAL_MS)
      }
    } catch {
      setError(cameraErrorMessage)
      stop()
    }
  }, [
    accept,
    cameraErrorMessage,
    cameraUnavailableMessage,
    detectorUnavailableMessage,
    formats,
    hasBarcodeDetector,
    onDetect,
    stop,
    videoRef,
    videoUnavailableMessage,
  ])

  useEffect(() => () => stop(), [stop])

  return { start, stop, running, error, hasBarcodeDetector, setError }
}
