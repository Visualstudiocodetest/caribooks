import { listBooks } from '@/services/books'
import { CatalogClient, type EtatItem, type CategorieItem } from './CatalogClient'
import { getAvailabilityMap } from '@/services/stocks'
import { listCatalog } from '@/services/catalog'

export const dynamic = 'force-dynamic'

export default async function CatalogPage() {
  const books = await listBooks().catch(() => [])
  // One batched availability request instead of fetching the whole /stock/ list
  // and reducing it here (the map is now computed server-side in a single query).
  const availability = await getAvailabilityMap().catch(() => ({} as Record<number, number>))
  // Reference lists fetched server-side alongside books/availability, instead of
  // a client-side waterfall after CatalogClient mounts.
  const etatList = await listCatalog<EtatItem>('etat-usures').catch(() => [])
  const categorieList = await listCatalog<CategorieItem>('categories').catch(() => [])

  // Show only books with remaining stock. availability keys are numbers server-side
  // but arrive as string keys once JSON-serialized — index defensively.
  const availAt = (id: number) => availability[id] ?? (availability as Record<string, number>)[String(id)] ?? 0
  const available = books.filter((b) => availAt(b.id_article) > 0)
  return (
    <CatalogClient
      books={available}
      availability={availability}
      etatList={etatList}
      categorieList={categorieList}
    />
  )
}
