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

async function tryOpenLibrary(isbn: string): Promise<OpenLibraryBook | null> {
  try {
    const url = `https://openlibrary.org/api/books?bibkeys=ISBN:${encodeURIComponent(isbn)}&format=json&jscmd=data`
    const res = await fetch(url, { signal: AbortSignal.timeout(8000) })
    if (!res.ok) return null
    const json = (await res.json()) as Record<string, OpenLibraryBook>
    const book = json[`ISBN:${isbn}`]
    if (book && book.title) return book
    return null
  } catch {
    return null
  }
}

async function tryGoogleBooks(isbn: string): Promise<OpenLibraryBook | null> {
  try {
    const url = `https://www.googleapis.com/books/v1/volumes?q=isbn:${encodeURIComponent(isbn)}&maxResults=1`
    const res = await fetch(url, { signal: AbortSignal.timeout(8000) })
    if (!res.ok) return null
    const json = (await res.json()) as {
      totalItems?: number
      items?: Array<{
        volumeInfo?: {
          title?: string
          subtitle?: string
          authors?: string[]
          publisher?: string
          publishedDate?: string
          description?: string
          imageLinks?: { thumbnail?: string; smallThumbnail?: string }
        }
      }>
    }
    if (!json.totalItems || !json.items?.length) return null
    const info = json.items[0]?.volumeInfo
    if (!info?.title) return null
    return {
      title: info.title,
      subtitle: info.subtitle,
      authors: (info.authors || []).map((name) => ({ name })),
      publishers: info.publisher ? [{ name: info.publisher }] : undefined,
      publish_date: info.publishedDate,
      notes: info.description,
      cover: info.imageLinks?.thumbnail
        ? {
            large: info.imageLinks.thumbnail.replace('zoom=1', 'zoom=3'),
            medium: info.imageLinks.thumbnail,
            small: info.imageLinks.smallThumbnail,
          }
        : undefined,
    }
  } catch {
    return null
  }
}

export async function lookupIsbn(isbn: string): Promise<OpenLibraryBook | null> {
  const clean = isbn.replace(/[^0-9Xx]/g, '').toUpperCase()
  if (!clean) return null
  const ol = await tryOpenLibrary(clean)
  if (ol) return ol
  return tryGoogleBooks(clean)
}
