'use client'

import Link from 'next/link'
import Image from 'next/image'
import { useState } from 'react'
import { useAuth } from '@/components/auth/AuthProvider'
import { useCart } from '@/components/cart/CartProvider'

export function Header() {
  const { isLoggedIn, isAdmin, setToken } = useAuth()
  const { count } = useCart()
  const [open, setOpen] = useState(false)

  return (
    <header className="site-header">
      <div className="container header-inner">
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <Link href="/" className="brand" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Image src="/logo-caritas.png" alt="Caribooks" width={140} height={36} />
          </Link>
          <nav className="main-nav">
            <Link className="muted" href="/catalog">
              Catalogue
            </Link>
            {isAdmin ? (
              <>
                <Link className="muted" href="/admin/books">
                  Interface admin
                </Link>
                <Link className="muted" href="/admin/lists">
                  Gérer les listes
                </Link>
              </>
            ) : null}
          </nav>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Link className="btn btnGhost" href="/cart">
            Panier ({count})
          </Link>
          {isLoggedIn ? (
            <button className="btn" onClick={() => setToken(null)} type="button">
              Déconnexion
            </button>
          ) : (
            <Link className="btn btnPrimary" href="/login">
              Connexion
            </Link>
          )}

          <button
            className="nav-toggle"
            aria-label="Toggle menu"
            aria-expanded={open}
            onClick={() => setOpen((s) => !s)}
            type="button"
          >
            <span className="hamburger" />
          </button>
        </div>
      </div>

      <div className={`mobile-nav ${open ? 'open' : ''}`}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <Link href="/catalog">Catalogue</Link>
          {isAdmin ? <Link href="/admin/books">Interface admin</Link> : null}
          {isAdmin ? <Link href="/admin/lists">Gérer les listes</Link> : null}
          <Link href="/cart">Panier ({count})</Link>
        </div>
      </div>
    </header>
  )
}
