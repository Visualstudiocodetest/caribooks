// Single source of truth for admin navigation destinations, shared by the
// header's "Back-office" dropdown menu and the /admin dashboard's own nav
// cards — previously each hand-maintained its own list, which is how the
// header ended up missing Stock/États d'usure/Utilisateurs after they were
// added to the dashboard but never mirrored in the header.

export type AdminNavItem = {
  href: string
  label: string
  icon: string
  desc: string
}

export type AdminNavGroup = {
  label: string
  items: AdminNavItem[]
}

export const ADMIN_NAV_GROUPS: AdminNavGroup[] = [
  {
    label: 'Catalogue',
    items: [
      { href: '/admin/books', label: 'Livres', icon: '📚', desc: 'Modifier, supprimer des livres' },
      { href: '/admin/books/new', label: 'Ajouter un livre', icon: '➕', desc: 'Scan ISBN ou saisie manuelle' },
      { href: '/admin/stock', label: 'Stock', icon: '🏷️', desc: 'Sources et quantités disponibles' },
      { href: '/admin/lists/etat-usures', label: "États d'usure", icon: '⭐', desc: 'Neuf, Bon état, Acceptable…' },
    ],
  },
  {
    label: 'Ventes',
    items: [
      { href: '/admin/orders', label: 'Commandes', icon: '📦', desc: 'Consulter, expédier, rembourser' },
    ],
  },
  {
    label: 'Comptes',
    items: [
      { href: '/admin/users', label: 'Utilisateurs', icon: '👥', desc: 'Rôles admin/utilisateur, suppression' },
    ],
  },
]
