'use client'

import { useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import type { BookRead } from '@/types/api'
import { Money } from '@/components/ui/Money'
import { useCart } from '@/components/cart/CartProvider'

function BookCover({ src, titre }: { src: string | null | undefined; titre: string }) {
  const [failed, setFailed] = useState(false)
  const isExternal = Boolean(src && src.startsWith('http') && !src.includes('/static/images/'))

  if (!src || failed) {
    return (
      <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 4 }}>
        <span style={{ fontSize: 32 }}>📖</span>
        <span style={{ fontSize: 11, fontWeight: 700, color: 'rgba(255,255,255,0.8)' }}>Pas d&apos;image</span>
      </div>
    )
  }

  return (
    <div className="book-image-inner">
      <Image src={src} alt={titre} fill style={{ objectFit: 'cover' }} sizes="(max-width: 640px) 45vw, 220px" unoptimized={isExternal} onError={() => setFailed(true)} />
    </div>
  )
}

export function BookCard({ book, available = null }: { book: BookRead; available?: number | null }) {
  const { addItem, items, setQuantity } = useCart()
  const [added, setAdded] = useState(false)
  const existing = items.find((i) => i.id_article === book.id_article)
  const inCart = Boolean(existing)
  // available === null means "unknown" (no stock rows tracked for this
  // article) — stay permissive, matching the backend's own create_ligne rule.
  const isSoldOut = available !== null && available < 1
  const atMax = Boolean(existing && available !== null && existing.quantity >= available)
  const isDisabled = isSoldOut || atMax

  function handleAddToCart(e: React.MouseEvent) {
    e.preventDefault()
    e.stopPropagation()
    if (isDisabled) return
    if (existing) {
      setQuantity(book.id_article, existing.quantity + 1)
    } else {
      addItem({ id_article: book.id_article, titre: book.titre, prix_chf: book.prix_chf, image_link: book.image_link })
    }
    setAdded(true)
    setTimeout(() => setAdded(false), 1500)
  }

  return (
    <Link href={`/books/${book.id_article}`} className="card book-card">
      <div className="book-image-wrap">
        <BookCover src={book.image_link} titre={book.titre} />
        {book.etat_libelle ? (
          <div style={{ position: 'absolute', top: 8, left: 8, background: 'rgba(0,0,0,0.55)', color: 'white', fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 999 }}>
            {book.etat_libelle}
          </div>
        ) : null}
      </div>

      <div className="cardPadding" style={{ display: 'grid', gap: 6 }}>
        <div>
          <div className="book-title" style={{ fontSize: 14 }}>{book.titre}</div>
          <div className="muted book-author">{book.auteur || '—'}</div>
        </div>
        <div className="book-meta" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 6 }}>
          <Money amount={book.prix_chf} />
          {book.categorie_libelles && book.categorie_libelles.length ? (
            <div className="muted" style={{ fontSize: 11 }}>{book.categorie_libelles[0]}</div>
          ) : null}
        </div>
        <button
          onClick={handleAddToCart}
          disabled={isDisabled}
          style={{
            marginTop: 2,
            width: '100%',
            padding: '6px 0',
            borderRadius: 8,
            border: 'none',
            cursor: isDisabled ? 'not-allowed' : 'pointer',
            fontWeight: 700,
            fontSize: 13,
            opacity: isDisabled ? 0.6 : 1,
            background: added ? '#065f46' : inCart ? '#e0f2fe' : 'var(--color-primary)',
            color: added ? 'white' : inCart ? '#0369a1' : 'white',
            transition: 'background 0.2s',
          }}
        >
          {isSoldOut
            ? 'Indisponible'
            : atMax
            ? 'Quantité max'
            : added
            ? '✓ Ajouté'
            : inCart
            ? 'Déjà dans le panier'
            : '+ Ajouter au panier'}
        </button>
      </div>
    </Link>
  )
}
