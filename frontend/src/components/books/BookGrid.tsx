import type { BookRead } from '@/types/api'
import { BookCard } from './BookCard'

export function BookGrid({
  books,
  availability,
}: {
  books: BookRead[]
  // Real remaining quantity per id_article, so BookCard can cap "Ajouter au
  // panier" instead of allowing unlimited clicks on an out-of-stock book.
  // Omitted (undefined) means "unknown" — BookCard stays permissive.
  availability?: Record<number, number>
}) {
  if (!books.length) {
    return <div className="muted">Aucun livre pour le moment.</div>
  }

  return (
    <div className="book-grid">
      {books.map((b) => (
        <BookCard key={b.id_article} book={b} available={availability?.[b.id_article] ?? null} />
      ))}
    </div>
  )
}
