'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ApiError } from '@/services/api'
import { cancelCommande, createCommande, createLigne } from '@/services/orders'
import type { CartItem } from '@/components/cart/CartProvider'

export function useCreateOrder() {
  const router = useRouter()
  const [status, setStatus] = useState<'idle' | 'loading' | 'error'>('idle')
  const [error, setError] = useState<string | null>(null)

  async function createOrder(shippingMethod: 'POST' | 'CLICK_COLLECT', items: CartItem[]) {
    setStatus('loading')
    setError(null)
    let commandeId: number | null = null
    try {
      const commande = await createCommande({ shipping_method: shippingMethod })
      commandeId = commande.id_commande
      await Promise.all(
        items.map((it) =>
          createLigne({
            id_commande: commande.id_commande,
            id_article: it.id_article,
            quantite: it.quantity,
          }),
        ),
      )
      // The cart is intentionally NOT cleared here — it's only cleared once
      // payment actually succeeds (see PaymentClient.tsx). Clearing it right
      // after creating the commande meant that cancelling or abandoning
      // payment left the user with an empty "panier" and no way to resume,
      // even though nothing had actually been paid for yet.
      router.push(`/payment?commandeId=${encodeURIComponent(String(commande.id_commande))}`)
    } catch (e) {
      if (commandeId) {
        // Release any stock a partially-successful line reservation already
        // grabbed, so a failed checkout attempt doesn't leave the item
        // reserved (and thus "unavailable") for up to 20 minutes while the
        // user retries.
        await cancelCommande(commandeId).catch(() => {})
      }
      const err = e as unknown
      setError(err instanceof ApiError ? err.message : 'Erreur lors de la commande. Réessayez.')
      setStatus('error')
    }
  }

  return { createOrder, status, error }
}
