'use client'

import { useQuery } from '@tanstack/react-query'
import { getAvailabilityMap } from '@/services/stocks'

/**
 * React Query hook for a single book's available quantity, backed by the
 * batched /stock/availability endpoint. Because React Query dedups identical
 * queries, many <AddToCartButton>/<CartItemRow> mounting at once no longer fan
 * out into N full /stock/ fetches — the old N+1.
 *
 * Returns { available, isLoading, refetch }; `available` is null until loaded.
 */
export function useAvailability(idLivre: number | null | undefined) {
  const enabled = typeof idLivre === 'number' && idLivre > 0
  const query = useQuery({
    queryKey: ['availability', idLivre],
    enabled,
    queryFn: async () => {
      const map = await getAvailabilityMap([idLivre as number])
      return map[idLivre as number] ?? 0
    },
  })
  return {
    available: query.data ?? null,
    isLoading: query.isLoading,
    refetch: query.refetch,
  }
}
