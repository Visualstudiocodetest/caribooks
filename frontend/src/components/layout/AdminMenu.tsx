'use client'

import Link from 'next/link'
import { useEffect, useRef, useState } from 'react'
import { usePathname } from 'next/navigation'
import { ADMIN_NAV_GROUPS } from '@/lib/adminNav'

// A single grouped dropdown replaces what used to be six flat text links
// (Ajouter un livre / Admin / Commandes / Stock / États d'usure / Types
// d'objets) crammed into the header — that many undifferentiated links was
// hard to scan and kept overflowing the nav row. This mirrors the /admin
// dashboard's own grouping (see lib/adminNav.ts) so there's one layout to
// keep in sync, not two.
export function AdminMenu() {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLElement>(null)
  const pathname = usePathname()

  useEffect(() => {
    function onPointerDown(e: PointerEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [])

  // A click on any link inside closes the menu; a route change is the same signal.
  useEffect(() => { setOpen(false) }, [pathname])

  return (
    <nav ref={ref} aria-label="Navigation administration" style={{ position: 'relative' }}>
      <button
        type="button"
        className="muted"
        onClick={() => setOpen((s) => !s)}
        aria-haspopup="true"
        aria-expanded={open}
        aria-controls="admin-menu-dropdown"
        style={{ background: 'none', border: 'none', font: 'inherit', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, padding: 0 }}
      >
        Back-office
        <span aria-hidden="true" style={{ fontSize: 10, transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }}>▾</span>
      </button>

      {open ? (
        <div
          id="admin-menu-dropdown"
          role="menu"
          className="card"
          style={{
            position: 'absolute',
            top: 'calc(100% + 10px)',
            left: 0,
            minWidth: 480,
            padding: 16,
            display: 'grid',
            gridTemplateColumns: 'repeat(3, minmax(140px, 1fr))',
            gap: 16,
            boxShadow: '0 12px 32px rgba(0,0,0,0.16)',
            zIndex: 50,
          }}
        >
          {ADMIN_NAV_GROUPS.map((group) => (
            <div key={group.label} style={{ display: 'grid', gap: 6, alignContent: 'start' }}>
              <div className="muted" style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                {group.label}
              </div>
              {group.items
                // "Ajouter un livre" is its own always-visible header link
                // (the single most common admin action), not just tucked
                // inside this dropdown -- skip it here to avoid showing it twice.
                .filter((item) => item.href !== '/admin/books/new')
                .map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  role="menuitem"
                  style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 6px', borderRadius: 8, color: 'var(--color-text)', fontWeight: 600, fontSize: 13.5 }}
                  onClick={() => setOpen(false)}
                >
                  <span aria-hidden="true">{item.icon}</span>
                  {item.label}
                </Link>
              ))}
            </div>
          ))}
        </div>
      ) : null}
    </nav>
  )
}
