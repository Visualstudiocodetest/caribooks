'use client'

import { useRouter, usePathname, useSearchParams, useParams } from 'next/navigation'
import { useState } from 'react'
import { apiFetch } from '@/services/api'

export default function LocalRedirectPage() {
  const params = useParams() as { ref?: string }
  const ref = params?.ref || 'unknown'
  const [loading, setLoading] = useState(false)
  const [ok, setOk] = useState<boolean | null>(null)
  const [err, setErr] = useState<string | null>(null)

  async function simulatePaid() {
    setLoading(true)
    setErr(null)
    try {
      const payload = { Id: `local-${ref}`, Status: 'PAID', Metadata: { reference: ref } }
      const r = await apiFetch('/orders/paiements/webhook/local', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      setOk(true)
    } catch (e: unknown) {
      setErr((e as Error).message || 'Erreur')
      setOk(false)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <h1>Simulation de paiement locale</h1>
      <div className="card cardPadding">
        <div style={{ fontWeight: 800 }}>Référence</div>
        <div className="muted">{ref}</div>
        <div style={{ marginTop: 12 }}>
          <button className="btn btnPrimary" onClick={simulatePaid} disabled={loading}>
            {loading ? 'Envoi…' : 'Simuler paiement réussi'}
          </button>
          <div style={{ marginTop: 8 }}>
            {ok === true ? <div className="muted">Webhook envoyé, paiement mis à jour.</div> : null}
            {ok === false ? <div className="muted">Erreur: {err}</div> : null}
          </div>
        </div>
      </div>
    </div>
  )
}
