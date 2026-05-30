import { apiFetch } from './api'
import type {
  CommandeCreate,
  CommandeRead,
  LigneCommandeCreate,
  PaiementCreate,
  PaiementRead,
  PaiementUpdate,
} from '@/types/api'

export function createCommande(payload: CommandeCreate): Promise<CommandeRead> {
  return apiFetch<CommandeRead>('/orders/commandes', {
    method: 'POST',
    auth: true,
    body: JSON.stringify(payload),
  })
}

export function createLigne(payload: LigneCommandeCreate) {
  return apiFetch('/orders/lignes', {
    method: 'POST',
    auth: true,
    body: JSON.stringify(payload),
  })
}

export function getCommande(id_commande: number): Promise<CommandeRead> {
  return apiFetch<CommandeRead>(`/orders/commandes/${id_commande}`, { auth: true })
}

export function createPaiement(payload: PaiementCreate): Promise<PaiementRead> {
  return apiFetch<PaiementRead>('/orders/paiements', {
    method: 'POST',
    auth: true,
    body: JSON.stringify(payload),
  })
}

export async function createPaiementPayrexx(payload: PaiementCreate): Promise<{ paiement: PaiementRead; redirect_url?: string | null } > {
  return apiFetch<any>('/orders/paiements/payrexx', {
    method: 'POST',
    auth: true,
    body: JSON.stringify(payload),
  })
}
export function getMyCommandes(): Promise<CommandeRead[]> {
  return apiFetch<CommandeRead[]>('/orders/commandes', { auth: true })
}

export function updatePaiement(id_paiement: number, payload: PaiementUpdate): Promise<PaiementRead> {
  return apiFetch<PaiementRead>(`/orders/paiements/${id_paiement}`, {
    method: 'PUT',
    auth: true,
    body: JSON.stringify(payload),
  })
}

