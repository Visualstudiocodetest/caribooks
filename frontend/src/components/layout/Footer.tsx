export function Footer() {
  return (
    <footer style={{ borderTop: '1px solid var(--color-border)', padding: '18px 0' }}>
      <div className="container" style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
        <div className="muted">© {new Date().getFullYear()} Caribooks</div>
        <div className="muted">Devise: CHF · Livraison: Suisse</div>
      </div>
    </footer>
  )
}
