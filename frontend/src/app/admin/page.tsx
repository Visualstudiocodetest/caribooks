'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { listBooks } from '@/services/books'
import { listAdminCommandes } from '@/services/admin'
import { ADMIN_NAV_GROUPS } from '@/lib/adminNav'

type Stats = { books: number; pending: number; paid: number; total: number }

export default function AdminHomePage() {
  const [stats, setStats] = useState<Stats | null>(null)

  useEffect(() => {
    let mounted = true
    Promise.all([listBooks().catch(() => []), listAdminCommandes().catch(() => [])]).then(
      ([books, commandes]) => {
        if (!mounted) return
        setStats({
          books: books.length,
          pending: commandes.filter((c) => ['CREATED', 'PENDING'].includes((c.statut || '').toUpperCase())).length,
          paid: commandes.filter((c) => ['PAID', 'CAPTURED', 'COMPLETED', 'SENT', 'AT_RECEPTION'].includes((c.statut || '').toUpperCase())).length,
          total: commandes.length,
        })
      },
    )
    return () => { mounted = false }
  }, [])

  return (
    <div style={{ display: 'grid', gap: 24, maxWidth: 900 }}>
      <h1 style={{ margin: 0 }}>Interface admin</h1>

      {stats ? (
        <section aria-labelledby="admin-stats-heading" style={{ display: 'grid', gap: 10 }}>
          <h2 id="admin-stats-heading" className="sr-only">Aperçu des statistiques</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12 }}>
            {[
              { label: 'Livres', value: stats.books, color: '#1d4ed8' },
              { label: 'Commandes en attente', value: stats.pending, color: '#b45309' },
              { label: 'Commandes actives', value: stats.paid, color: '#065f46' },
              { label: 'Commandes total', value: stats.total, color: '#374151' },
            ].map((s) => (
              <div key={s.label} className="card" style={{ padding: '14px 16px' }} aria-label={`${s.value} ${s.label}`}>
                <div style={{ fontSize: 28, fontWeight: 900, color: s.color }} aria-hidden="true">{s.value}</div>
                <div className="muted" style={{ fontSize: 12, marginTop: 2 }} aria-hidden="true">{s.label}</div>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {ADMIN_NAV_GROUPS.map((group) => (
        <nav key={group.label} aria-label={group.label} style={{ display: 'grid', gap: 10 }}>
          <h2 className="muted" style={{ margin: 0, fontSize: 13, textTransform: 'uppercase', letterSpacing: '0.04em' }}>{group.label}</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12 }}>
            {group.items.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="card"
                style={{ padding: '16px', display: 'grid', gap: 6, textDecoration: 'none', transition: 'box-shadow 0.15s' }}
              >
                <div style={{ fontSize: 24 }} aria-hidden="true">{item.icon}</div>
                <div style={{ fontWeight: 800, fontSize: 15, color: 'var(--color-text)' }}>{item.label}</div>
                <div className="muted" style={{ fontSize: 12 }}>{item.desc}</div>
              </Link>
            ))}
          </div>
        </nav>
      ))}
    </div>
  )
}
