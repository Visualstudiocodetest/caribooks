'use client'

import { useCart } from './CartProvider'
import { useEffect, useState } from 'react'
import { getAvailableQuantityForArticle } from '@/services/stocks'

export function AddToCartButton(props: {
  id_article: number
  titre: string
  prix_chf: number
  image_link?: string | null
}) {
  const { addItem, items, setQuantity } = useCart()
  const [available, setAvailable] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let mounted = true
    getAvailableQuantityForArticle(props.id_article).then((q) => {
      if (mounted) setAvailable(q)
    })
    return () => {
      mounted = false
    }
  }, [props.id_article])
  const existing = items.find((i) => i.id_article === props.id_article)

  const isDisabled =
    loading ||
    (available !== null && available < 1) ||
    (existing && available !== null && existing.quantity >= available)

  return (
    <button
      type="button"
      className="btn btnPrimary"
      onClick={async () => {
        if (loading) return
        setLoading(true)
        try {
          const q = available === null ? await getAvailableQuantityForArticle(props.id_article) : available
          setAvailable(q)
          const avail = q || 0
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
        } finally {
          setLoading(false)
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
