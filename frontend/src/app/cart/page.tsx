'use client'

import Link from 'next/link'
import { useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useCart } from '@/components/cart/CartProvider'
import { useAuth } from '@/components/auth/AuthProvider'
import { Money } from '@/components/ui/Money'
import CartItemRow from '@/components/cart/CartItemRow'
import { ApiError } from '@/services/api'
import { createCommande, createLigne } from '@/services/orders'

function makeNumeroCommande() {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  const t = String(now.getTime()).slice(-6)
  return `CB-${y}${m}${d}-${t}`
}

export default function CartPage() {
  const router = useRouter()
  const { isLoggedIn } = useAuth()
  const { items, total, removeItem, setQuantity, clear } = useCart()
  const [shippingMethod, setShippingMethod] = useState<'POST' | 'CLICK_COLLECT'>('POST')
  const [status, setStatus] = useState<'idle' | 'loading' | 'error'>('idle')
  const [error, setError] = useState<string | null>(null)

  const shippingFee = shippingMethod === 'CLICK_COLLECT' ? 1.0 : 9.0
  const finalTotal = Math.round((total + shippingFee) * 100) / 100
  const canOrder = useMemo(() => isLoggedIn && items.length > 0, [isLoggedIn, items.length])

  async function onOrder() {
    setStatus('loading')
    setError(null)
    try {
      const commande = await createCommande({
        numero_commande: makeNumeroCommande(),
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

  return (
    <div className="container page-main">
      <div className="content-center">
        <h1 style={{ margin: 0 }}>Panier</h1>

        {items.length === 0 ? (
          <div className="card cardPadding">
            <div className="muted">Votre panier est vide.</div>
            <div style={{ marginTop: 12 }}>
              <Link className="btn btnPrimary" href="/catalog">
                Parcourir le catalogue
              </Link>
            </div>
          </div>
        ) : (
          <>
            <div className="card cardPadding">
              {items.map((it) => (
                <CartItemRow key={it.id_article} item={it} onRemove={removeItem} onSetQuantity={setQuantity} />
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

            {!isLoggedIn ? (
              <div className="card cardPadding">
                <div style={{ fontWeight: 700 }}>Connexion requise</div>
                <div className="muted">Connectez-vous pour finaliser votre commande.</div>
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 8 }}>
                  <Link className="btn btnPrimary" href="/login?returnTo=/cart">Se connecter</Link>
                  <Link className="btn" href="/register?returnTo=/cart">Créer un compte</Link>
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button
                  className="btn btnPrimary"
                  type="button"
                  onClick={onOrder}
                  disabled={!canOrder || status === 'loading'}
                >
                  {status === 'loading' ? 'Création de la commande…' : 'Passer commande →'}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
