import { apiFetch } from './api'
import type { CommandeRead } from '@/types/api'

export async function listAdminCommandes(): Promise<CommandeRead[]> {
  return apiFetch<CommandeRead[]>('/orders/admin/commandes', { auth: true })
}

export async function adminSetCommandeStatus(id_commande: number, payload: Partial<CommandeRead>) {
  return apiFetch<CommandeRead>(`/orders/admin/commandes/${id_commande}/status`, {
    method: 'PUT',
    auth: true,
    body: JSON.stringify(payload),
  })
}

export async function adminAdvanceCommande(id_commande: number) {
  return apiFetch<CommandeRead>(`/orders/admin/commandes/${id_commande}/advance`, {
    method: 'POST',
    auth: true,
  })
}
