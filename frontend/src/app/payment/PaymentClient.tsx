'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { useAuth } from '@/components/auth/AuthProvider'
import { Money } from '@/components/ui/Money'
import { ApiError } from '@/services/api'
import type { CommandeRead } from '@/types/api'
import { createPaiementPostFinance, getCommande, pollPaiementPostFinance } from '@/services/orders'

function makeReference() {
  return `local-${Date.now()}`
}

export function PaymentClient() {
  const searchParams = useSearchParams()
  const commandeId = Number(searchParams.get('commandeId'))
  const { isLoggedIn } = useAuth()

  const [commande, setCommande] = useState<CommandeRead | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const ready = useMemo(
    () => isLoggedIn && Number.isFinite(commandeId) && commandeId > 0,
    [isLoggedIn, commandeId],
  )

  useEffect(() => {
    if (!ready) return
    let mounted = true
    setLoading(true)
    setError(null)
    getCommande(commandeId)
      .then(async (cmd) => {
        if (!mounted) return
        setCommande(cmd)
        // If we have a paiementId coming from the provider redirect, poll its status
        const paiementIdParam = Number(searchParams.get('paiementId'))
        if (Number.isFinite(paiementIdParam) && paiementIdParam > 0) {
          const pollResp = await pollPaiementPostFinance(paiementIdParam)
          if (!mounted) return
          const statut = pollResp?.paiement?.statut
          if (statut && ['CAPTURED', 'PAID', 'COMPLETED', 'AUTHORIZED', 'FULFILL'].includes(String(statut).toUpperCase())) {
            // Payment successful — redirect to orders or show success state
            window.location.href = '/account/orders'
            return
          }
          setError('Paiement en attente ou non confirmé. Réessayez ou contactez le support.')
          return
        }

        // Otherwise create a new PostFinance payment and redirect
        const resp = await createPaiementPostFinance({
          id_commande: cmd.id_commande,
          reference_externe: makeReference(),
          montant_chf: cmd.montant_total_chf,
          statut: 'PENDING',
        })
        if (!mounted) return
        if (resp && resp.redirect_url) {
          // redirect to provider
          window.location.href = resp.redirect_url
          return
        }
        setError(
          typeof resp?.error === 'string'
            ? resp.error
            : 'PostFinance checkout is not available. Check the backend configuration.',
        )
      })
      .catch((e: unknown) => {
        if (!mounted) return
        setError(e instanceof ApiError ? e.message : 'Erreur paiement')
      })
      .finally(() => {
        if (!mounted) return
        setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [commandeId, ready])

  if (!isLoggedIn) {
    return (
      <div className="card" style={{ padding: 16, display: 'grid', gap: 10 }}>
        <div style={{ fontWeight: 900 }}>Connexion requise</div>
        <div className="muted">Connectez-vous pour effectuer le paiement.</div>
        <Link className="btn btnPrimary" href="/login">
          Se connecter
        </Link>
      </div>
    )
  }

  if (!Number.isFinite(commandeId) || commandeId <= 0) {
    return (
      <div className="card" style={{ padding: 16, display: 'grid', gap: 10 }}>
        <div style={{ fontWeight: 900 }}>Commande manquante</div>
        <div className="muted">Revenez au panier pour relancer une commande.</div>
        <Link className="btn btnPrimary" href="/cart">
          Aller au panier
        </Link>
      </div>
    )
  }

  return (
    <div style={{ display: 'grid', gap: 16, maxWidth: 820, margin: '0 auto' }}>
      <h1 style={{ margin: 0 }}>Paiement</h1>

      {loading ? <div className="muted">Chargement…</div> : null}
      {error ? <div className="muted">{error}</div> : null}

      {commande ? (
        <div className="card" style={{ padding: 16, display: 'grid', gap: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
            <div>
              <div style={{ fontWeight: 900 }}>Commande</div>
              <div className="muted">{commande.numero_commande}</div>
            </div>
            <Money amount={commande.montant_total_chf} />
          </div>

          <div className="muted">
            Vous allez être redirigé vers PostFinance Checkout pour finaliser le paiement.
          </div>

          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <Link className="btn" href="/catalog">
              Retour au catalogue
            </Link>
          </div>
        </div>
      ) : null}
    </div>
  )
}