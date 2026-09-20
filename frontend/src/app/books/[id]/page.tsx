import { cache } from 'react'
import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import Image from 'next/image'
import Link from 'next/link'
import { getBook } from '@/services/books'
import { Money } from '@/components/ui/Money'
import { AddToCartButton } from '@/components/cart/AddToCartButton'
import { isExternalImage } from '@/lib/images'

export const dynamic = 'force-dynamic'

// generateMetadata and the page both need the book. React's `cache` memoises the
// call for the duration of a single request, so the backend is still hit once.
const loadBook = cache(async (id: string) => {
  try {
    return await getBook(Number(id))
  } catch {
    return null
  }
})

export async function generateMetadata(props: PageProps<'/books/[id]'>): Promise<Metadata> {
  const { id } = await props.params
  const book = await loadBook(id)
  if (!book) return { title: 'Livre introuvable' }

  const description =
    book.description?.slice(0, 160) ||
    `${book.titre}${book.auteur ? ` — ${book.auteur}` : ''}, livre de seconde main à ${book.prix_chf} CHF.`

  return {
    title: book.titre,
    description,
    openGraph: {
      title: book.titre,
      description,
      type: 'article',
      images: book.image_link ? [book.image_link] : undefined,
    },
  }
}

export default async function BookDetailPage(props: PageProps<'/books/[id]'>) {
  const { id } = await props.params
  const book = await loadBook(id)
  if (!book) notFound()

  const isExternal = isExternalImage(book.image_link)

  return (
    <div className="content-center">
      <div style={{ marginBottom: 4 }}>
        <Link className="btn btnGhost" href="/" style={{ fontSize: 13, padding: '4px 10px' }}>
          <span aria-hidden="true">←</span> Retour au catalogue
        </Link>
      </div>

      <div className="card cardPadding">
        <div className="book-detail-grid">
          <div className="card book-image-wrap large" style={{ position: 'relative' }}>
            {book.image_link ? (
              <div className="book-image-inner">
                <Image
                  src={book.image_link}
                  alt={`Couverture de ${book.titre}`}
                  fill
                  style={{ objectFit: 'cover' }}
                  sizes="(max-width: 640px) 100vw, 320px"
                  unoptimized={isExternal}
                />
              </div>
            ) : (
              <div
                style={{
                  width: '100%',
                  height: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexDirection: 'column',
                  gap: 6,
                  background: 'var(--color-surface)',
                }}
              >
                <span aria-hidden="true" style={{ fontSize: 48, opacity: 0.4 }}>📖</span>
                <span className="muted" style={{ fontSize: 12 }}>Pas d&apos;image</span>
              </div>
            )}
            {book.etat_libelle ? (
              <div
                style={{
                  position: 'absolute',
                  top: 10,
                  left: 10,
                  background: 'rgba(0,0,0,0.6)',
                  color: 'white',
                  fontSize: 11,
                  fontWeight: 700,
                  padding: '3px 10px',
                  borderRadius: '999px',
                }}
              >
                {book.etat_libelle}
              </div>
            ) : null}
          </div>

          <div style={{ display: 'grid', gap: 14, alignContent: 'start' }}>
            <div>
              <h1 style={{ margin: 0, lineHeight: 1.2 }}>{book.titre}</h1>
              {book.auteur ? <div className="muted" style={{ marginTop: 4 }}>{book.auteur}</div> : null}
            </div>

            <div>
              <Money amount={book.prix_chf} />
              <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
                + CHF 9.00 frais de port (livraison)
              </div>
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {book.editeur ? (
                <span className="muted" style={{ fontSize: 13 }}>Éditeur&nbsp;: {book.editeur}</span>
              ) : null}
              {book.langue ? (
                <span className="muted" style={{ fontSize: 13 }}>Langue&nbsp;: {book.langue}</span>
              ) : null}
              {book.date_publication ? (
                <span className="muted" style={{ fontSize: 13 }}>Pub.&nbsp;: {book.date_publication}</span>
              ) : null}
            </div>

            {book.description ? (
              <div style={{ lineHeight: 1.6, fontSize: 14 }}>{book.description}</div>
            ) : null}

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
  )
}
