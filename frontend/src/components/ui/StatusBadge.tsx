import { statusColor, statusLabel } from '@/lib/orderStatus'

export function StatusBadge({ statut }: { statut: string }) {
  const color = statusColor(statut)
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 10px',
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 700,
        background: `${color}18`,
        color,
        border: `1px solid ${color}40`,
        whiteSpace: 'nowrap',
      }}
    >
      {statusLabel(statut)}
    </span>
  )
}
