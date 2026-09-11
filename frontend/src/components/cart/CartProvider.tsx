'use client'

import { createContext, useContext, useMemo } from 'react'
import { useLocalStorageState } from '@/hooks/useLocalStorage'
import type { ReactNode } from 'react'

export type CartItem = {
  id_article: number
  titre: string
  prix_chf: number
  image_link?: string | null
  quantity: number
}

type CartContextValue = {
  items: CartItem[]
  count: number
  total: number
  hydrated: boolean
  addItem: (item: Omit<CartItem, 'quantity'>) => void
  removeItem: (id_article: number) => void
  setQuantity: (id_article: number, quantity: number) => void
  clear: () => void
}

const CartContext = createContext<CartContextValue | null>(null)

export function CartProvider({ children }: { children: ReactNode }) {
  const { value: items, setValue: setItems, hydrated } = useLocalStorageState<CartItem[]>('caribooks_cart', [])

  const value = useMemo<CartContextValue>(() => {
    const count = items.reduce((acc, it) => acc + it.quantity, 0)
    const total = items.reduce((acc, it) => acc + it.quantity * it.prix_chf, 0)

    return {
      items,
      count,
      total,
      hydrated,
      addItem: (item) =>
        setItems((prev) => {
          const existing = prev.find((p) => p.id_article === item.id_article)
          if (!existing) return [...prev, { ...item, quantity: 1 }]
          return prev.map((p) =>
            p.id_article === item.id_article ? { ...p, quantity: p.quantity + 1 } : p,
          )
        }),
      removeItem: (id_article) => setItems((prev) => prev.filter((p) => p.id_article !== id_article)),
      setQuantity: (id_article, quantity) =>
        setItems((prev) =>
          prev
            .map((p) => (p.id_article === id_article ? { ...p, quantity } : p))
            .filter((p) => p.quantity > 0),
        ),
      clear: () => setItems([]),
    }
  }, [items, setItems, hydrated])

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>
}

export function useCart() {
  const ctx = useContext(CartContext)
  if (!ctx) throw new Error('useCart must be used within CartProvider')
  return ctx
}
