import { apiFetch } from './api'
import type { BookRead, BookCreate } from '@/types/api'

export function listBooks(): Promise<BookRead[]> {
  return apiFetch<BookRead[]>('/books/')
}

export function getBook(id_article: number): Promise<BookRead> {
  return apiFetch<BookRead>(`/books/${id_article}`)
}

// Returns null when the ISBN is not in the catalogue (backend replies 200 + null).
export function getBookByIsbn(isbn: string): Promise<BookRead | null> {
  return apiFetch<BookRead | null>(`/books/by-isbn/${encodeURIComponent(isbn)}`)
}

export function createBook(payload: BookCreate): Promise<BookRead> {
  return apiFetch<BookRead>('/books/', { method: 'POST', auth: true, body: JSON.stringify(payload) })
}

export function updateBook(id_article: number, payload: Partial<Omit<BookRead, 'id_article'>>): Promise<BookRead> {
  return apiFetch<BookRead>(`/books/${id_article}`, { method: 'PUT', auth: true, body: JSON.stringify(payload) })
}

export function deleteBook(id_article: number): Promise<void> {
  return apiFetch<void>(`/books/${id_article}`, { method: 'DELETE', auth: true })
}
