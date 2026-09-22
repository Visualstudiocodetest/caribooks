'use client'

import { createContext, useContext, useMemo } from 'react'
import { useLocalStorageState } from '@/hooks/useLocalStorage'
import type { ReactNode } from 'react'

export type CartItem = {
  id_livre: number
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
  removeItem: (id_livre: number) => void
  setQuantity: (id_livre: number, quantity: number) => void
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
          const existing = prev.find((p) => p.id_livre === item.id_livre)
          if (!existing) return [...prev, { ...item, quantity: 1 }]
          return prev.map((p) =>
            p.id_livre === item.id_livre ? { ...p, quantity: p.quantity + 1 } : p,
          )
        }),
      removeItem: (id_livre) => setItems((prev) => prev.filter((p) => p.id_livre !== id_livre)),
      setQuantity: (id_livre, quantity) =>
        setItems((prev) =>
          prev
            .map((p) => (p.id_livre === id_livre ? { ...p, quantity } : p))
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
