import { apiFetch } from './api'
import type { BookRead, BookCreate } from '@/types/api'

export function listBooks(): Promise<BookRead[]> {
  return apiFetch<BookRead[]>('/books/')
}

export function getBook(id_livre: number): Promise<BookRead> {
  return apiFetch<BookRead>(`/books/${id_livre}`)
}

// Returns null when the ISBN is not in the catalogue (backend replies 200 + null).
export function getBookByIsbn(isbn: string): Promise<BookRead | null> {
  return apiFetch<BookRead | null>(`/books/by-isbn/${encodeURIComponent(isbn)}`)
}

export function createBook(payload: BookCreate): Promise<BookRead> {
  return apiFetch<BookRead>('/books/', { method: 'POST', auth: true, body: JSON.stringify(payload) })
}

export function updateBook(id_livre: number, payload: Partial<Omit<BookRead, 'id_livre'>>): Promise<BookRead> {
  return apiFetch<BookRead>(`/books/${id_livre}`, { method: 'PUT', auth: true, body: JSON.stringify(payload) })
}

export function deleteBook(id_livre: number): Promise<void> {
  return apiFetch<void>(`/books/${id_livre}`, { method: 'DELETE', auth: true })
}

/**
 * Retirer de la vente un livre épuisé dans tous les magasins.
 *
 * Le backend supprime le livre s'il n'a jamais été commandé, sinon il le
 * désactive (`actif = false`) pour préserver les lignes de commande — d'où le
 * `BookRead | null` en retour. Renvoie une erreur 409 s'il reste du stock.
 */
export function removeOutOfStockBook(id_livre: number): Promise<BookRead | null> {
  return apiFetch<BookRead | null>(`/books/${id_livre}/retirer`, { method: 'POST', auth: true })
}
