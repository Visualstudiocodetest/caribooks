import Image from 'next/image'
import { getBook } from '@/services/books'
import { Money } from '@/components/ui/Money'
import { AddToCartButton } from '@/components/cart/AddToCartButton'

export const dynamic = 'force-dynamic'

export default async function BookDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const book = await getBook(Number(id))
  const isExternal = Boolean(book.image_link && book.image_link.startsWith('http') && !book.image_link.includes('/static/images/'))

  return (
    <div className="content-center">
      <div className="card cardPadding">
      <div className="book-detail-grid">
          <div className="card book-image-wrap large">
            {book.image_link ? (
              <div className="book-image-inner">
                <Image
                  src={book.image_link}
                  alt={book.titre}
                  fill
                  style={{ objectFit: 'cover' }}
                  sizes="(max-width: 640px) 100vw, 320px"
                  unoptimized={isExternal}
                />
              </div>
            ) : (
              <div className="muted" style={{ fontWeight: 700 }}>
                Pas d'image
              </div>
            )}
          </div>

          <div style={{ display: 'grid', gap: 10 }}>
            <div>
              <h1 style={{ margin: 0 }}>{book.titre}</h1>
              <div className="muted">{book.auteur || '—'}</div>
            </div>

            <div style={{ display: 'flex', gap: 14, alignItems: 'baseline', flexWrap: 'wrap' }}>
              <div style={{ display: 'grid', gap: 4 }}>
                <Money amount={book.prix_chf} />
                <div className="muted">Frais de port: 9 CHF</div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              {book.editeur ? <span className="muted">Éditeur: {book.editeur}</span> : null}
              {book.langue ? <span className="muted">Langue: {book.langue}</span> : null}
              {book.date_publication ? (
                <span className="muted">Publication: {book.date_publication}</span>
              ) : null}
              {book.etat_libelle ? <span className="muted">État: {book.etat_libelle}</span> : null}
              {book.categorie_libelles && book.categorie_libelles.length ? (
                <span className="muted">Catégorie: {book.categorie_libelles[0]}</span>
              ) : null}
            </div>

            {book.description ? (
              <div className="muted" style={{ lineHeight: 1.55 }}>
                {book.description}
              </div>
            ) : null}

            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <AddToCartButton
                id_article={book.id_article}
                titre={book.titre}
                prix_chf={book.prix_chf}
                image_link={book.image_link}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
