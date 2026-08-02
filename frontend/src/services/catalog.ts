import { apiFetch } from './api'

// Catalog reference data (type-objets, etat-usures, categories). Centralizes the
// endpoint strings that were previously hard-coded with inline apiFetch calls in
// CatalogClient, the admin book forms and the admin list pages.

export type CatalogItem = { id?: number; libelle: string; code?: string } & Record<string, unknown>

export type CatalogResource = 'type-objets' | 'etat-usures' | 'categories'

export function listCatalog<T = CatalogItem>(resource: CatalogResource): Promise<T[]> {
  return apiFetch<T[]>(`/catalog/${resource}`)
}

export function createCatalogItem<T = CatalogItem>(resource: CatalogResource, body: Record<string, unknown>): Promise<T> {
  return apiFetch<T>(`/catalog/${resource}`, { method: 'POST', auth: true, body: JSON.stringify(body) })
}

export function updateCatalogItem<T = CatalogItem>(resource: CatalogResource, id: number, body: Record<string, unknown>): Promise<T> {
  return apiFetch<T>(`/catalog/${resource}/${id}`, { method: 'PUT', auth: true, body: JSON.stringify(body) })
}

export function deleteCatalogItem(resource: CatalogResource, id: number): Promise<void> {
  return apiFetch<void>(`/catalog/${resource}/${id}`, { method: 'DELETE', auth: true })
}
