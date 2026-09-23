"use client"

import { useEffect } from 'react'
import { Money } from '@/components/ui/Money'
import type { CartItem } from './CartProvider'
import { useAvailability } from '@/hooks/useAvailability'

export default function CartItemRow({
  item,
  onRemove,
  onSetQuantity,
}: {
  item: CartItem
  onRemove: (id_livre: number) => void
  onSetQuantity: (id_livre: number, q: number) => void
}) {
  const { available } = useAvailability(item.id_livre)
  const outOfStock = available !== null && available < 1

  useEffect(() => {
    // Clamp DOWN to the available quantity — but only when at least 1 is available.
    // Clamping to 0 would make setQuantity drop the line entirely (quantity <= 0 is
    // filtered out), silently removing an item the user still has in their cart.
    // A transiently out-of-stock item stays visible and is flagged instead.
    if (available !== null && available >= 1 && item.quantity > available) {
      onSetQuantity(item.id_livre, available)
    }
  }, [available, item.quantity, item.id_livre, onSetQuantity])

  const decrease = () => {
    if (item.quantity <= 1) return onRemove(item.id_livre)
    onSetQuantity(item.id_livre, item.quantity - 1)
  }

  const increase = () => {
    if (available === null || item.quantity + 1 > available) return
    onSetQuantity(item.id_livre, item.quantity + 1)
  }

  return (
    <div className="cart-item-row">
      <div className="cart-item-info">
        <div style={{ fontWeight: 800 }}>{item.titre}</div>
        <div className="muted">
          <Money amount={item.prix_chf} />
        </div>
        {outOfStock ? (
          <div style={{ color: '#dc2626', fontSize: 12, fontWeight: 700 }} role="status">
            Indisponible — retirez cet article
          </div>
        ) : null}
      </div>

      <div className="qty-controls" role="group" aria-labelledby={`qty-label-${item.id_livre}`}>
        <span id={`qty-label-${item.id_livre}`} className="visually-hidden">
          {`Quantité pour ${item.titre}`}
        </span>
        <button className="btn" type="button" onClick={decrease} aria-label={`Diminuer la quantité de ${item.titre}`}>
          −
        </button>
        <div className="cart-qty-count" aria-live="polite">
          {item.quantity}
        </div>
        <button
          className="btn"
          type="button"
          onClick={increase}
          aria-label={`Augmenter la quantité de ${item.titre}`}
          disabled={available !== null && item.quantity >= available}
        >
          +
        </button>
      </div>
      <div className="remove-wrap">
        <button
          className="btn"
          type="button"
          onClick={() => onRemove(item.id_livre)}
          aria-label={`Retirer ${item.titre} du panier`}
        >
          Retirer
        </button>
      </div>
    </div>
  )
}
