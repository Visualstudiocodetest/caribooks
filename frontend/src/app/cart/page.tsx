'use client'

import Link from 'next/link'
import { useMemo, useState } from 'react'
import { useCart } from '@/components/cart/CartProvider'
import { useAuth } from '@/components/auth/AuthProvider'
import { Money } from '@/components/ui/Money'
import CartItemRow from '@/components/cart/CartItemRow'
import { useCreateOrder } from '@/hooks/useCreateOrder'

// Mirrors backend/services/order_service.py's SHIPPING_FEES_CHF — the server is
// the source of truth for the actual charge, this is only for display/estimate.
const SHIPPING_FEES_CHF = { POST: 9.0, CLICK_COLLECT: 1.0 } as const

export default function CartPage() {
  const { isLoggedIn } = useAuth()
  const { items, total, removeItem, setQuantity } = useCart()
  const [shippingMethod, setShippingMethod] = useState<'POST' | 'CLICK_COLLECT'>('POST')
  const { createOrder, status, error } = useCreateOrder()

  const shippingFee = SHIPPING_FEES_CHF[shippingMethod]
  const finalTotal = Math.round((total + shippingFee) * 100) / 100
  const canOrder = useMemo(() => isLoggedIn && items.length > 0, [isLoggedIn, items.length])

  function onOrder() {
    void createOrder(shippingMethod, items)
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
                  <span>Livraison par la Poste Suisse — <strong>{SHIPPING_FEES_CHF.POST.toFixed(2)} CHF</strong></span>
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
                  <input
                    type="radio"
                    name="shipping"
                    value="CLICK_COLLECT"
                    checked={shippingMethod === 'CLICK_COLLECT'}
                    onChange={() => setShippingMethod('CLICK_COLLECT')}
                  />
                  <span>Retrait en magasin Caritas — <strong>{SHIPPING_FEES_CHF.CLICK_COLLECT.toFixed(2)} CHF</strong></span>
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
