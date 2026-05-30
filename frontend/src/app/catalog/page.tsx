import { listBooks } from '@/services/books'
import { CatalogClient } from './CatalogClient'
import { apiFetch } from '@/services/api'
import { Stock } from '@/types/api'

export const dynamic = 'force-dynamic'

export default async function CatalogPage() {
  const books = await listBooks().catch(() => [])
  // Fetch stock info server-side and filter out books with zero available quantity
  let stocks: Stock[] = []
  try {
    stocks = await apiFetch('/stock/')
  } catch {
    stocks = []
  }

  const map = new Map<number, number>()
  for (const s of stocks) {
    const cur = map.get(s.id_article) || 0
    const avail = (s.quantite_disponible || 0) - (s.quantite_reservee || 0)
    map.set(s.id_article, cur + avail)
  }

  const available = books.filter((b) => (map.get(b.id_article) || 0) > 0)
  return <CatalogClient books={available} />
}
