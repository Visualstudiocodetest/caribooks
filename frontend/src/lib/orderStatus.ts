// Single source of truth for order-status presentation, shared by the customer
// order history and the admin order back-office (previously duplicated verbatim
// in both). Keys mirror the backend commande.statut vocabulary.

export const STATUS_LABELS: Record<string, string> = {
  CREATED: 'En attente',
  PENDING: 'En attente',
  PAID: 'Payée',
  CAPTURED: 'Payée',
  COMPLETED: 'Payée',
  SENT: 'Expédiée',
  AT_RECEPTION: 'Prête à retirer',
  FINISHED: 'Terminée',
  REFUNDED: 'Remboursée',
  FAILED: 'Échouée',
  CANCELLED: 'Annulée',
}

export const STATUS_COLORS: Record<string, string> = {
  CREATED: '#b45309',
  PENDING: '#b45309',
  PAID: '#065f46',
  CAPTURED: '#065f46',
  COMPLETED: '#065f46',
  SENT: '#1d4ed8',
  AT_RECEPTION: '#1d4ed8',
  FINISHED: '#374151',
  REFUNDED: '#6b7280',
  FAILED: '#dc2626',
  CANCELLED: '#6b7280',
}

export function statusLabel(statut: string | null | undefined): string {
  return STATUS_LABELS[(statut || '').toUpperCase()] || statut || '—'
}

export function statusColor(statut: string | null | undefined): string {
  return STATUS_COLORS[(statut || '').toUpperCase()] || '#6b7280'
}

// Mirrors backend ALL_STATUSES (services/order_service.py) — the full set the
// admin override endpoint (PUT /orders/admin/commandes/{id}/status) accepts.
export const ALL_STATUSES = [
  'CREATED',
  'PENDING',
  'PAID',
  'CAPTURED',
  'COMPLETED',
  'SENT',
  'AT_RECEPTION',
  'FINISHED',
  'CANCELLED',
  'REFUNDED',
] as const

// CANCELLED and REFUNDED are deliberately excluded from the "force status"
// override: both have dedicated endpoints (cancel/refund) that reconcile
// stock and payment records. Setting them via the raw status override does
// a bare `commande.statut = ...` write with no reconciliation, which silently
// strands sold stock as unavailable-but-never-released.
export const FORCE_STATUS_OPTIONS = ALL_STATUSES.filter(
  (s) => s !== 'CANCELLED' && s !== 'REFUNDED'
)
