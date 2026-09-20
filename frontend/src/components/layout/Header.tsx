'use client'

import Link from 'next/link'
import Image from 'next/image'
import { useState } from 'react'
import { useAuth } from '@/components/auth/AuthProvider'
import { useCart } from '@/components/cart/CartProvider'
import { usePathname } from 'next/navigation'
import { ADMIN_NAV_GROUPS } from '@/lib/adminNav'
import { AdminMenu } from './AdminMenu'

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
        <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          <Link href="/" className="brand" style={{ display: 'flex', alignItems: 'center', gap: 8 }} onClick={closeMenu}>
            <Image src="/logo-caritas.jpg" alt="Caritas" width={40} height={40} style={{ borderRadius: 6 }} priority />
            <span>Caribooks</span>
          </Link>
          <nav className="main-nav" aria-label="Navigation principale">
            <Link className="muted" href="/">Catalogue</Link>
            {isAdmin ? <Link className="muted" href="/admin/books/new">Ajouter un livre</Link> : null}
            {isLoggedIn ? (
              <>
                <Link className="muted" href="/account">Mon compte</Link>
                <Link className="muted" href="/account/orders">Mes commandes</Link>
              </>
            ) : null}
            {isAdmin ? <AdminMenu /> : null}
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
            aria-label={open ? 'Fermer le menu de navigation' : 'Ouvrir le menu de navigation'}
            aria-expanded={open}
            aria-controls="mobile-nav-menu"
            onClick={() => setOpen((s) => !s)}
            type="button"
          >
            <span className="hamburger" aria-hidden="true" />
          </button>
        </div>
      </div>

      <nav id="mobile-nav-menu" className={`mobile-nav ${open ? 'open' : ''}`} aria-label="Navigation mobile">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <Link href="/" onClick={closeMenu}>Catalogue</Link>
          {isAdmin ? <Link href="/admin/books/new" onClick={closeMenu}>➕ Ajouter un livre</Link> : null}

          {isAdmin ? ADMIN_NAV_GROUPS.map((group) => (
            <div key={group.label} style={{ display: 'grid', gap: 8, paddingTop: 4 }}>
              <div className="muted" style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                {group.label}
              </div>
              {group.items
                .filter((item) => item.href !== '/admin/books/new')
                .map((item) => (
                <Link key={item.href} href={item.href} onClick={closeMenu} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span aria-hidden="true">{item.icon}</span>
                  {item.label}
                </Link>
              ))}
            </div>
          )) : null}

          {isLoggedIn ? (
            <div style={{ display: 'grid', gap: 8, paddingTop: 4 }}>
              <div className="muted" style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Mon espace
              </div>
              <Link href="/account" onClick={closeMenu}>Mon compte</Link>
              <Link href="/account/orders" onClick={closeMenu}>Mes commandes</Link>
            </div>
          ) : null}

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
      </nav>
    </header>
  )
}
