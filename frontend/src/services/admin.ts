import { apiFetch } from './api'
import type { CommandeAdminRead, CommandeRead, LigneCommandeAdminRead } from '@/types/api'

export async function adminGetLignes(id_commande: number): Promise<LigneCommandeAdminRead[]> {
  return apiFetch<LigneCommandeAdminRead[]>(`/orders/admin/commandes/${id_commande}/lignes`, { auth: true })
}

export async function listAdminCommandes(): Promise<CommandeAdminRead[]> {
  return apiFetch<CommandeAdminRead[]>('/orders/admin/commandes', { auth: true })
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
