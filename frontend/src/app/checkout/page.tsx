'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import { useAuth } from '@/components/auth/AuthProvider'
import { useCart } from '@/components/cart/CartProvider'
import { Money } from '@/components/ui/Money'
import { ApiError } from '@/services/api'
import { createCommande, createLigne } from '@/services/orders'
import { useRouter } from 'next/navigation'

function makeNumeroCommande() {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  const t = String(now.getTime()).slice(-6)
  return `CB-${y}${m}${d}-${t}`
}

export default function CheckoutPage() {
  const router = useRouter()
  const { isLoggedIn } = useAuth()
  const { items, total, clear } = useCart()
  const [status, setStatus] = useState<'idle' | 'loading' | 'error'>('idle')
  const [error, setError] = useState<string | null>(null)
  const [shippingMethod, setShippingMethod] = useState<'POST' | 'CLICK_COLLECT'>('POST')

  const shippingFee = shippingMethod === 'CLICK_COLLECT' ? 1.0 : 9.0
  const finalTotal = Math.round((total + shippingFee) * 100) / 100
  const canCheckout = useMemo(() => isLoggedIn && items.length > 0, [isLoggedIn, items.length])

  async function onConfirm() {
    setStatus('loading')
    setError(null)
    try {
      const numero_commande = makeNumeroCommande()
      const commande = await createCommande({
        numero_commande,
        montant_total_chf: finalTotal,
        statut: 'CREATED',
        shipping_method: shippingMethod,
        frais_port_chf: shippingFee,
      })
      await Promise.all(
        items.map((it) =>
          createLigne({
            id_commande: commande.id_commande,
            id_article: it.id_article,
            quantite: it.quantity,
            prix_unitaire_chf: it.prix_chf,
          }),
        ),
      )
      clear()
      router.push(`/payment?commandeId=${encodeURIComponent(String(commande.id_commande))}`)
    } catch (e) {
      const err = e as unknown
      setError(err instanceof ApiError ? err.message : 'Erreur lors de la commande. Réessayez.')
      setStatus('error')
    }
  }

  if (!isLoggedIn) {
    return (
      <div className="content-center" style={{ maxWidth: 560 }}>
        <h1 style={{ margin: 0 }}>Commande</h1>
        <div className="card cardPadding">
          <div style={{ fontWeight: 800 }}>Connexion requise</div>
          <div className="muted">Connectez-vous pour finaliser votre commande.</div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <Link className="btn btnPrimary" href="/login?returnTo=/checkout">
              Se connecter
            </Link>
            <Link className="btn" href="/register?returnTo=/checkout">
              Créer un compte
            </Link>
          </div>
        </div>
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="content-center" style={{ maxWidth: 560 }}>
        <h1 style={{ margin: 0 }}>Commande</h1>
        <div className="card cardPadding">
          <div className="muted">Votre panier est vide.</div>
          <Link className="btn btnPrimary" href="/catalog">
            Voir le catalogue
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="content-center" style={{ maxWidth: 560 }}>
      <h1 style={{ margin: 0 }}>Commande</h1>

      <div className="card cardPadding">
        <div style={{ fontWeight: 700, marginBottom: 4 }}>Récapitulatif</div>
        {items.map((it) => (
          <div key={it.id_article} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14 }}>
            <span className="muted">{it.titre} × {it.quantity}</span>
            <Money amount={it.prix_chf * it.quantity} />
          </div>
        ))}
      </div>

      <div className="card cardPadding">
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Livraison</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
            <input
              type="radio"
              name="shipping"
              value="POST"
              checked={shippingMethod === 'POST'}
              onChange={() => setShippingMethod('POST')}
            />
            <span>Livraison par la Poste Suisse — <strong>9.00 CHF</strong></span>
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
            <input
              type="radio"
              name="shipping"
              value="CLICK_COLLECT"
              checked={shippingMethod === 'CLICK_COLLECT'}
              onChange={() => setShippingMethod('CLICK_COLLECT')}
            />
            <span>Retrait en magasin Caritas — <strong>1.00 CHF</strong></span>
          </label>
        </div>
      </div>

      <div className="card" style={{ padding: '12px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ fontWeight: 900 }}>Total à payer</div>
          <div className="muted" style={{ fontSize: 13 }}>CHF · Livraison Suisse</div>
        </div>
        <Money amount={finalTotal} />
      </div>

      {error ? <div className="banner-error">{error}</div> : null}

      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        <button
          className="btn btnPrimary"
          type="button"
          onClick={onConfirm}
          disabled={!canCheckout || status === 'loading'}
          style={{ flex: 1 }}
        >
          {status === 'loading' ? 'Création de la commande…' : 'Continuer vers le paiement →'}
        </button>
        <Link className="btn" href="/cart">
          Retour au panier
        </Link>
      </div>
    </div>
  )
}
