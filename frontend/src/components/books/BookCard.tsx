import Link from 'next/link'
import Image from 'next/image'
import type { BookRead } from '@/types/api'
import { Money } from '@/components/ui/Money'

export function BookCard({ book }: { book: BookRead }) {
  const isExternal = Boolean(book.image_link && book.image_link.startsWith('http') && !book.image_link.includes('/static/images/'))

  return (
    <Link href={`/books/${book.id_article}`} className="card book-card">
      <div className="book-image-wrap">
        {book.image_link ? (
          <div className="book-image-inner">
            <Image
              src={book.image_link}
              alt={book.titre}
              fill
              style={{ objectFit: 'cover' }}
              sizes="(max-width: 640px) 45vw, 360px"
              unoptimized={isExternal}
            />
          </div>
        ) : (
          <div className="muted" style={{ fontWeight: 700 }}>
            Livre
          </div>
        )}
      </div>
      <div className="cardPadding">
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
          <div>
            <div className="book-title">{book.titre}</div>
            <div className="muted book-author">{book.auteur || '—'}</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            {book.etat_libelle ? <div className="muted">{book.etat_libelle}</div> : null}
            {book.categorie_libelles && book.categorie_libelles.length ? (
              <div className="muted">{book.categorie_libelles[0]}</div>
            ) : null}
          </div>
        </div>

        <div className="book-meta">
          <Money amount={book.prix_chf} />
        </div>
      </div>
    </Link>
  )
}
