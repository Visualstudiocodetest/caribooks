'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { listBooks } from '@/services/books'
import { listAdminCommandes } from '@/services/admin'

type Stats = { books: number; pending: number; paid: number; total: number }

const NAV_ITEMS = [
  { href: '/admin/books', label: 'Livres', icon: '📚', desc: 'Ajouter, modifier, supprimer des livres' },
  { href: '/admin/orders', label: 'Commandes', icon: '📦', desc: 'Consulter et faire avancer les commandes' },
  { href: '/admin/lists/categories', label: 'Catégories', icon: '🏷️', desc: 'Gérer les catégories de livres' },
  { href: '/admin/lists/etat-usures', label: 'États d\'usure', icon: '⭐', desc: 'Neuf, Bon état, Acceptable…' },
  { href: '/admin/lists/type-objets', label: 'Types d\'objets', icon: '🗂️', desc: 'Livre, DVD, Jeu…' },
]

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
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12 }}>
          {[
            { label: 'Livres', value: stats.books, color: '#1d4ed8' },
            { label: 'Commandes en attente', value: stats.pending, color: '#b45309' },
            { label: 'Commandes actives', value: stats.paid, color: '#065f46' },
            { label: 'Commandes total', value: stats.total, color: '#374151' },
          ].map((s) => (
            <div key={s.label} className="card" style={{ padding: '14px 16px' }}>
              <div style={{ fontSize: 28, fontWeight: 900, color: s.color }}>{s.value}</div>
              <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>{s.label}</div>
            </div>
          ))}
        </div>
      ) : null}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12 }}>
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="card"
            style={{ padding: '16px', display: 'grid', gap: 6, textDecoration: 'none', transition: 'box-shadow 0.15s' }}
          >
            <div style={{ fontSize: 24 }}>{item.icon}</div>
            <div style={{ fontWeight: 800, fontSize: 15, color: 'var(--color-text)' }}>{item.label}</div>
            <div className="muted" style={{ fontSize: 12 }}>{item.desc}</div>
          </Link>
        ))}
      </div>
    </div>
  )
}
