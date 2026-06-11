import { apiFetch } from './api'

export type OpenLibraryBook = {
  title?: string
  authors?: Array<{ name?: string }>
  publishers?: Array<{ name?: string }>
  publish_date?: string
  cover?: { large?: string; medium?: string; small?: string }
  notes?: string
  by_statement?: string
  subtitle?: string
}

export async function lookupIsbn(isbn: string): Promise<OpenLibraryBook | null> {
  const clean = isbn.replace(/[^0-9Xx]/g, '').toUpperCase()
  if (!clean) return null
  try {
    return await apiFetch<OpenLibraryBook>(`/books/isbn-metadata/${encodeURIComponent(clean)}`)
  } catch {
    return null
  }
}
