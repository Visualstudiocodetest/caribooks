'use client'

import Link from 'next/link'

export default function ArticleCategoriesPage() {
  return (
    <div style={{ display: 'grid', gap: 12 }}>
      <h2>Article categories</h2>
      <p className="muted">This view maps to the same categories used by articles.</p>
      <Link className="btn" href="/admin/lists/categories">Gérer les catégories</Link>
    </div>
  )
}
