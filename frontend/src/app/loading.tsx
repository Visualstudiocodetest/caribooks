// Instant Suspense fallback while a Server Component route fetches its data,
// so a slow backend call shows the shell rather than a blank navigation.
export default function Loading() {
  return (
    <div className="content-center" role="status" aria-live="polite">
      <div className="card cardPadding">
        <p className="muted" style={{ margin: 0 }}>Chargement…</p>
      </div>
    </div>
  )
}
