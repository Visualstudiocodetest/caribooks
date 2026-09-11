'use client'

import Link from 'next/link'

export default function AdminListsIndex() {
  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <h1 style={{ margin: 0 }}>Gérer les listes</h1>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
        {[
          { href: '/admin/lists/categories', label: 'Catégories', icon: '🏷️', desc: 'Romans, BD, Sciences…' },
          { href: '/admin/lists/etat-usures', label: 'États d\'usure', icon: '⭐', desc: 'Neuf, Bon état, Acceptable…' },
          { href: '/admin/lists/type-objets', label: 'Types d\'objets', icon: '🗂️', desc: 'Livre, DVD, Jeu…' },
        ].map((item) => (
          <Link key={item.href} href={item.href} className="card" style={{ padding: 16, display: 'grid', gap: 6, textDecoration: 'none' }}>
            <div style={{ fontSize: 22 }}>{item.icon}</div>
            <div style={{ fontWeight: 800, color: 'var(--color-text)' }}>{item.label}</div>
            <div className="muted" style={{ fontSize: 12 }}>{item.desc}</div>
          </Link>
        ))}
      </div>
    </div>
  )
}
