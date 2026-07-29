'use client'

import { useCallback, useEffect, useRef, useState, type RefObject } from 'react'

const DEFAULT_FORMATS: BarcodeFormat[] = ['ean_13', 'ean_8', 'upc_a', 'upc_e', 'code_128']
const DEDUPE_WINDOW_MS = 1500
const DETECT_INTERVAL_MS = 350
const VIDEO_MOUNT_RETRIES = 20
const VIDEO_MOUNT_RETRY_DELAY_MS = 100

export interface UseBarcodeScannerOptions {
  formats?: BarcodeFormat[]
  cameraUnavailableMessage?: string
  cameraErrorMessage?: string
  videoUnavailableMessage?: string
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
        // eslint-disable-next-line no-await-in-loop
        await new Promise((r) => setTimeout(r, VIDEO_MOUNT_RETRY_DELAY_MS))
        video = videoRef.current
      }
      if (!video) {
        setError(videoUnavailableMessage)
        stop()
        return
      }
      video.srcObject = stream
      await video.play()

      if (hasBarcodeDetector) {
        const detector = new BarcodeDetector({ formats })

        intervalRef.current = window.setInterval(async () => {
          const v = videoRef.current
          if (!v || v.readyState < 2) return
          try {
            const codes = await detector.detect(v)
            if (!codes.length) return
            const raw = (codes[0]?.rawValue || '').trim()
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
  }, [cameraErrorMessage, cameraUnavailableMessage, formats, hasBarcodeDetector, onDetect, stop, videoRef, videoUnavailableMessage])

  useEffect(() => () => stop(), [stop])

  return { start, stop, running, error, hasBarcodeDetector, setError }
}
