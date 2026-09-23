import { apiFetch } from './api'
import { SourceStock, Stock } from '@/types/api'

export async function listStocks(): Promise<Stock[]> {
  return apiFetch<Stock[]>('/stock/')
}

export function listSources(): Promise<SourceStock[]> {
  return apiFetch<SourceStock[]>('/stock/sources')
}

export function createSource(payload: { libelle: string; type_source: string; description?: string }): Promise<SourceStock> {
  return apiFetch<SourceStock>('/stock/sources', { method: 'POST', auth: true, body: JSON.stringify(payload) })
}

export function deleteSource(id_source_stock: number): Promise<void> {
  return apiFetch<void>(`/stock/sources/${id_source_stock}`, { method: 'DELETE', auth: true })
}

export function createStock(payload: { id_livre: number; id_source_stock: number; quantite_disponible: number }): Promise<Stock> {
  return apiFetch<Stock>('/stock/', { method: 'POST', auth: true, body: JSON.stringify(payload) })
}

export function incrementStock(id_stock: number, qty = 1): Promise<Stock> {
  return apiFetch<Stock>(`/stock/${id_stock}/increment`, { method: 'POST', auth: true, body: JSON.stringify({ qty }) })
}

export function decrementStock(id_stock: number, qty = 1): Promise<Stock> {
  return apiFetch<Stock>(`/stock/${id_stock}/decrement`, { method: 'POST', auth: true, body: JSON.stringify({ qty }) })
}

export function deleteStock(id_stock: number): Promise<void> {
  return apiFetch<void>(`/stock/${id_stock}`, { method: 'DELETE', auth: true })
}

/**
 * Batched availability: one request returns { id_livre: available } for the
 * given books (or the whole catalogue when `livreIds` is omitted). Replaces
 * the old per-book getAvailableQuantityForArticle which fetched the entire
 * /stock/ list once per item (N+1).
 */
export async function getAvailabilityMap(livreIds?: number[]): Promise<Record<number, number>> {
  const qs = livreIds && livreIds.length ? `?livre_ids=${livreIds.join(',')}` : ''
  return apiFetch<Record<number, number>>(`/stock/availability${qs}`)
}
