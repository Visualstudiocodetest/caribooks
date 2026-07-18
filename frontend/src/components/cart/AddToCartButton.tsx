'use client'

import { useCart } from './CartProvider'
import { useAvailability } from '@/hooks/useAvailability'

export function AddToCartButton(props: {
  id_article: number
  titre: string
  prix_chf: number
  image_link?: string | null
}) {
  const { addItem, items, setQuantity } = useCart()
  const { available, isLoading: loading } = useAvailability(props.id_article)
  const existing = items.find((i) => i.id_article === props.id_article)

  const isDisabled =
    loading ||
    (available !== null && available < 1) ||
    Boolean(existing && available !== null && existing.quantity >= available)

  return (
    <button
      type="button"
      className="btn btnPrimary"
      onClick={() => {
        const avail = available ?? 0
        if (avail < 1) return
        const currentQty = existing ? existing.quantity : 0
        if (currentQty + 1 > avail) return

        if (existing) {
          setQuantity(props.id_article, currentQty + 1)
        } else {
          addItem({
            id_article: props.id_article,
            titre: props.titre,
            prix_chf: props.prix_chf,
            image_link: props.image_link,
          })
        }
      }}
      disabled={isDisabled}
    >
      {available !== null && available < 1
        ? 'Indisponible'
        : existing && available !== null && existing.quantity >= available
        ? 'Quantité max'
        : loading
        ? 'Achat…'
        : 'Acheter'}
    </button>
  )
}
