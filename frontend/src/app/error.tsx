'use client' // Error boundaries must be Client Components.

import { useEffect } from 'react'

export default function ErrorPage({
  error,
  retry,
}: {
  error: Error & { digest?: string }
  retry: () => void
}) {
  useEffect(() => {
    // `digest` is the only identifier available for a server-side error: the
    // real message is withheld from the client in production builds.
    console.error(error)
  }, [error])

  return (
    <div className="content-center">
      <div className="card cardPadding" style={{ display: 'grid', gap: 12, justifyItems: 'start' }}>
        <h1 style={{ margin: 0 }}>Une erreur est survenue</h1>
        <p className="muted" style={{ margin: 0 }}>
          La page n&apos;a pas pu être affichée. Vous pouvez réessayer.
        </p>
        {error.digest ? (
          <p className="muted" style={{ margin: 0, fontSize: 12 }}>Référence : {error.digest}</p>
        ) : null}
        <button className="btn btnPrimary" type="button" onClick={() => retry()}>
          Réessayer
        </button>
      </div>
    </div>
  )
}
