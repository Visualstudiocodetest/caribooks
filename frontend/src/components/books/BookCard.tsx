'use client'

import { useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import type { BookRead } from '@/types/api'
import { Money } from '@/components/ui/Money'

function BookCover({ src, titre }: { src: string | null | undefined; titre: string }) {
  const [failed, setFailed] = useState(false)
  const isExternal = Boolean(src && src.startsWith('http') && !src.includes('/static/images/'))

  if (!src || failed) {
    return (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexDirection: 'column',
          gap: 4,
        }}
      >
        <span style={{ fontSize: 32 }}>📖</span>
        <span style={{ fontSize: 11, fontWeight: 700, color: 'rgba(255,255,255,0.8)' }}>Pas d&apos;image</span>
      </div>
    )
  }

  return (
    <div className="book-image-inner">
      <Image
        src={src}
        alt={titre}
        fill
        style={{ objectFit: 'cover' }}
        sizes="(max-width: 640px) 45vw, 220px"
        unoptimized={isExternal}
        onError={() => setFailed(true)}
      />
    </div>
  )
}

export function BookCard({ book }: { book: BookRead }) {
  return (
    <Link href={`/books/${book.id_article}`} className="card book-card">
      <div className="book-image-wrap">
        <BookCover src={book.image_link} titre={book.titre} />
        {book.etat_libelle ? (
          <div
            style={{
              position: 'absolute',
              top: 8,
              left: 8,
              background: 'rgba(0,0,0,0.55)',
              color: 'white',
              fontSize: 10,
              fontWeight: 700,
              padding: '2px 7px',
              borderRadius: '999px',
            }}
          >
            {book.etat_libelle}
          </div>
        ) : null}
      </div>

      <div className="cardPadding" style={{ display: 'grid', gap: 6 }}>
        <div>
          <div className="book-title" style={{ fontSize: 14 }}>{book.titre}</div>
          <div className="muted book-author">{book.auteur || '—'}</div>
        </div>
        <div className="book-meta">
          <Money amount={book.prix_chf} />
          {book.categorie_libelles && book.categorie_libelles.length ? (
            <div className="muted" style={{ fontSize: 11 }}>{book.categorie_libelles[0]}</div>
          ) : null}
        </div>
      </div>
    </Link>
  )
}
