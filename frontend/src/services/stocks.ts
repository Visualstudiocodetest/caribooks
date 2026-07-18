import { apiFetch } from './api'
import { Stock } from '@/types/api'

export async function listStocks(): Promise<Stock[]> {
  return apiFetch<Stock[]>('/stock/')
}

export async function getAvailableQuantityForArticle(id_article: number) {
  const stocks: Stock[] = await listStocks()
  return stocks
    .filter((s) => s.id_article === id_article)
    .reduce((acc, s) => acc + Math.max(0, (s.quantite_disponible || 0) - (s.quantite_reservee || 0)), 0)
}
