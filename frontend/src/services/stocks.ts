import { apiFetch } from './api'
import { Stock } from '@/types/api'

export async function listStocks(): Promise<Stock[]> {
  return apiFetch<Stock[]>('/stock/')
}

/**
 * Batched availability: one request returns { id_article: available } for the
 * given articles (or the whole catalogue when `articleIds` is omitted). Replaces
 * the old per-article getAvailableQuantityForArticle which fetched the entire
 * /stock/ list once per item (N+1).
 */
export async function getAvailabilityMap(articleIds?: number[]): Promise<Record<number, number>> {
  const qs = articleIds && articleIds.length ? `?article_ids=${articleIds.join(',')}` : ''
  return apiFetch<Record<number, number>>(`/stock/availability${qs}`)
}
