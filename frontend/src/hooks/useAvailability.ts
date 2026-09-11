'use client'

import { useQuery } from '@tanstack/react-query'
import { getAvailabilityMap } from '@/services/stocks'

/**
 * React Query hook for a single article's available quantity, backed by the
 * batched /stock/availability endpoint. Because React Query dedups identical
 * queries, many <AddToCartButton>/<CartItemRow> mounting at once no longer fan
 * out into N full /stock/ fetches — the old N+1.
 *
 * Returns { available, isLoading, refetch }; `available` is null until loaded.
 */
export function useAvailability(idArticle: number | null | undefined) {
  const enabled = typeof idArticle === 'number' && idArticle > 0
  const query = useQuery({
    queryKey: ['availability', idArticle],
    enabled,
    queryFn: async () => {
      const map = await getAvailabilityMap([idArticle as number])
      return map[idArticle as number] ?? 0
    },
  })
  return {
    available: query.data ?? null,
    isLoading: query.isLoading,
    refetch: query.refetch,
  }
}
