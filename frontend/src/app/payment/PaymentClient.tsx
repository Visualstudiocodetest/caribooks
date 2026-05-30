'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { useAuth } from '@/components/auth/AuthProvider'
import { useCart } from '@/components/cart/CartProvider'
import { Money } from '@/components/ui/Money'
import { ApiError } from '@/services/api'
import type { CommandeRead, PaiementRead } from '@/types/api'
import { createPaiement, createPaiementPayrexx, getCommande, updatePaiement } from '@/services/orders'

function makeReference() {
  return `local-${Date.now()}`
}

export function PaymentClient() {
  const searchParams = useSearchParams()
  const commandeId = Number(searchParams.get('commandeId'))
  const { isLoggedIn } = useAuth()
  const { clear } = useCart()

  const [commande, setCommande] = useState<CommandeRead | null>(null)
  const [paiement, setPaiement] = useState<PaiementRead | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [paying, setPaying] = useState(false)

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
        const resp = await createPaiementPayrexx({
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
        // fallback: set local paiement object
        setPaiement(resp.paiement)
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

  async function onSimulatePaid() {
    if (!paiement) return
    setPaying(true)
    setError(null)
    try {
      const updated = await updatePaiement(paiement.id_paiement, {
        statut: 'PAID',
        date_paiement: new Date().toISOString(),
      })
      setPaiement(updated)
      clear()
    } catch (e: unknown) {
      setError(e instanceof ApiError ? e.message : 'Paiement impossible')
    } finally {
      setPaying(false)
    }
  }

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

          {paiement ? (
            <div className="card" style={{ padding: 12 }}>
              <div style={{ fontWeight: 800 }}>Statut: {paiement.statut}</div>
              <div className="muted">Référence: {paiement.reference_externe}</div>
            </div>
          ) : null}

          <button
            className="btn btnPrimary"
            type="button"
            onClick={onSimulatePaid}
            disabled={paying || paiement?.statut === 'PAID'}
          >
            {paiement?.statut === 'PAID' ? 'Payé' : paying ? 'Paiement…' : 'Simuler paiement (dev)'}
          </button>

          <div className="muted">
            Cette étape enregistre un paiement via l’API (`/orders/paiements`). L’intégration réelle Payrexx
            pourra remplacer ce bouton plus tard.
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