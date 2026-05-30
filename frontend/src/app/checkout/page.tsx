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
  return `PB-${y}${m}${d}-${t}`
}

export default function CheckoutPage() {
  const router = useRouter()
  const { isLoggedIn } = useAuth()
  const { items, total, clear } = useCart()
  const [status, setStatus] = useState<'idle' | 'loading' | 'done' | 'error'>('idle')
  const [message, setMessage] = useState<string | null>(null)
  const [shippingMethod, setShippingMethod] = useState<'POST' | 'CLICK_COLLECT'>('POST')

  const canCheckout = useMemo(() => isLoggedIn && items.length > 0, [isLoggedIn, items.length])

  async function onConfirm() {
    setStatus('loading')
    setMessage(null)
    try {
      const numero_commande = makeNumeroCommande()
      const shippingFee = shippingMethod === 'CLICK_COLLECT' ? 1.0 : 9.0
      const finalTotal = Math.round((total + shippingFee) * 100) / 100
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
      setStatus('done')
      setMessage(`Commande créée: ${commande.numero_commande}`)
      router.push(`/payment?commandeId=${encodeURIComponent(String(commande.id_commande))}`)
    } catch (e) {
      const err = e as unknown
      if (err instanceof ApiError) setMessage(err.message)
      else setMessage('Erreur lors de la commande.')
      setStatus('error')
    }
  }

  return (
    <div className="content-center">
      <h1 style={{ margin: 0 }}>Commande</h1>

      {!isLoggedIn ? (
        <div className="card cardPadding">
          <div style={{ fontWeight: 800 }}>Connexion requise</div>
          <div className="muted">Vous devez être connecté pour créer une commande.</div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <Link className="btn btnPrimary" href="/login">
              Se connecter
            </Link>
            <Link className="btn" href="/register">
              Créer un compte
            </Link>
          </div>
        </div>
      ) : items.length === 0 ? (
        <div className="card cardPadding">
          <div className="muted">Votre panier est vide.</div>
          <Link className="btn btnPrimary" href="/catalog">
            Voir le catalogue
          </Link>
        </div>
      ) : (
        <div className="card cardPadding">
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
            <div>
              <div style={{ fontWeight: 900 }}>Total</div>
              <div className="muted">Devise CHF · Livraison Suisse</div>
            </div>
            <div style={{ display: 'grid', gap: 8 }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <label>
                  <input type="radio" name="shipping" value="POST" checked={shippingMethod === 'POST'} onChange={() => setShippingMethod('POST')} /> Livraison (9 CHF)
                </label>
                <label>
                  <input type="radio" name="shipping" value="CLICK_COLLECT" checked={shippingMethod === 'CLICK_COLLECT'} onChange={() => setShippingMethod('CLICK_COLLECT')} /> Retrait (1 CHF)
                </label>
              </div>
              <Money amount={Math.round((total + (shippingMethod === 'CLICK_COLLECT' ? 1 : 9)) * 100) / 100} />
            </div>
          </div>

          {message ? (
            <div
              className="card"
              style={{
                padding: 12,
              }}
            >
              {message}
            </div>
          ) : null}

          <button className="btn btnPrimary" type="button" onClick={onConfirm} disabled={!canCheckout || status === 'loading'}>
            {status === 'loading' ? 'Création…' : 'Confirmer la commande'}
          </button>
          <div className="muted">Le paiement est finalisé à l’étape suivante.</div>
        </div>
      )}
    </div>
  )
}
