'use client'

import Link from 'next/link'
import Image from 'next/image'
import { useState } from 'react'
import { useAuth } from '@/components/auth/AuthProvider'
import { useCart } from '@/components/cart/CartProvider'
import { usePathname } from 'next/navigation'

export function Header() {
  const { isLoggedIn, isAdmin, setToken } = useAuth()
  const { count } = useCart()
  const [open, setOpen] = useState(false)
  const pathname = usePathname()

  function closeMenu() {
    setOpen(false)
  }

  return (
    <header className="site-header">
      <div className="container header-inner">
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <Link href="/" className="brand" style={{ display: 'flex', alignItems: 'center', gap: 8 }} onClick={closeMenu}>
            <Image src="/Logo-caritas.svg" alt="Caribooks" width={140} height={36} priority />
          </Link>
          <nav className="main-nav">
            <Link className="muted" href="/catalog">Catalogue</Link>
            {isAdmin ? (
              <>
                <Link className="muted" href="/scan">Scanner</Link>
                <Link className="muted" href="/admin/books">Admin</Link>
              </>
            ) : null}
            {isLoggedIn ? (
              <Link className="muted" href="/account">Mon compte</Link>
            ) : null}
          </nav>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Link
            className="btn btnGhost"
            href="/cart"
            style={{ position: 'relative', gap: 6 }}
            aria-label={`Panier, ${count} article${count !== 1 ? 's' : ''}`}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z"/>
              <line x1="3" y1="6" x2="21" y2="6"/>
              <path d="M16 10a4 4 0 01-8 0"/>
            </svg>
            {count > 0 ? (
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'var(--color-primary)',
                color: 'white',
                borderRadius: '999px',
                fontSize: 11,
                fontWeight: 700,
                minWidth: 18,
                height: 18,
                padding: '0 4px',
              }}>
                {count}
              </span>
            ) : null}
          </Link>

          {isLoggedIn ? (
            <button className="btn btnGhost" onClick={() => setToken(null)} type="button">
              Déconnexion
            </button>
          ) : pathname !== '/login' ? (
            <Link className="btn btnPrimary" href={`/login${pathname !== '/' ? `?returnTo=${encodeURIComponent(pathname)}` : ''}`}>
              Connexion
            </Link>
          ) : null}

          <button
            className="nav-toggle"
            aria-label="Menu"
            aria-expanded={open}
            onClick={() => setOpen((s) => !s)}
            type="button"
          >
            <span className="hamburger" />
          </button>
        </div>
      </div>

      <div className={`mobile-nav ${open ? 'open' : ''}`}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <Link href="/catalog" onClick={closeMenu}>Catalogue</Link>
          {isAdmin ? <Link href="/scan" onClick={closeMenu}>Scanner un ISBN</Link> : null}
          {isAdmin ? <Link href="/admin/books" onClick={closeMenu}>Interface admin</Link> : null}
          {isLoggedIn ? <Link href="/account" onClick={closeMenu}>Mon compte</Link> : null}
          {isLoggedIn ? <Link href="/account/orders" onClick={closeMenu}>Mes commandes</Link> : null}
          <Link href="/cart" onClick={closeMenu}>
            Panier {count > 0 ? `(${count})` : ''}
          </Link>
          {isLoggedIn ? (
            <button
              className="btn"
              onClick={() => { setToken(null); closeMenu() }}
              type="button"
              style={{ justifyContent: 'flex-start', padding: 0, border: 'none', background: 'none', color: 'var(--color-primary)', fontWeight: 600 }}
            >
              Déconnexion
            </button>
          ) : (
            <Link href="/login" onClick={closeMenu}>Se connecter</Link>
          )}
        </div>
      </div>
    </header>
  )
}
