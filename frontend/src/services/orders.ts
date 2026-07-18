import { apiFetch } from './api'
import type { PostFinanceIframeSession } from '@/types/postfinance'
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

export function cancelCommande(id_commande: number): Promise<CommandeRead> {
  return apiFetch<CommandeRead>(`/orders/commandes/${id_commande}/cancel`, {
    method: 'POST',
    auth: true,
  })
}

export function createPaiement(payload: PaiementCreate): Promise<PaiementRead> {
  return apiFetch<PaiementRead>('/orders/paiements', {
    method: 'POST',
    auth: true,
    body: JSON.stringify(payload),
  })
}

export function createPaiementPostFinance(payload: PaiementCreate): Promise<PostFinanceIframeSession> {
  return apiFetch<PostFinanceIframeSession>('/orders/paiements/postfinance', {
    method: 'POST',
    auth: true,
    body: JSON.stringify(payload),
  })
}

export function confirmPaiementPostFinance(id_paiement: number): Promise<{ paiement: PaiementRead }> {
  return apiFetch<{ paiement: PaiementRead }>(`/orders/paiements/${id_paiement}/confirm-postfinance`, {
    method: 'POST',
    auth: true,
  })
}

export function pollPaiementPostFinance(id_paiement: number): Promise<{ paiement: PaiementRead }> {
  return apiFetch<{ paiement: PaiementRead }>(`/orders/paiements/${id_paiement}/poll-postfinance`, { auth: true })
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
