'use client' // Error boundaries must be Client Components.

// Last-resort boundary for errors thrown by the root layout itself. It replaces
// the root layout when active, so it must render its own <html>/<body>.
export default function GlobalError({
  error,
  retry,
}: {
  error: Error & { digest?: string }
  retry: () => void
}) {
  return (
    <html lang="fr">
      <body style={{ fontFamily: 'system-ui, sans-serif', padding: 32 }} role="alert">
        <h1>Une erreur est survenue</h1>
        <p>L&apos;application n&apos;a pas pu démarrer.</p>
        {error.digest ? <p style={{ fontSize: 12 }}>Référence : {error.digest}</p> : null}
        <button type="button" onClick={() => retry()}>Réessayer</button>
      </body>
    </html>
  )
}
