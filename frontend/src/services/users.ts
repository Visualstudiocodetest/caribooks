import { apiFetch } from './api'
import type { UserRead } from '@/types/api'

// Admin-only user management (GET /users/, PUT/DELETE /users/{id}). Distinct
// from services/auth.ts's getCurrentUser/updateCurrentUser, which are the
// self-service /users/me endpoints any logged-in user can call.

export function listUsers(): Promise<UserRead[]> {
  return apiFetch<UserRead[]>('/users/', { auth: true })
}

export function setUserRole(id_utilisateur: number, role: string): Promise<UserRead> {
  return apiFetch<UserRead>(`/users/${id_utilisateur}`, {
    method: 'PUT',
    auth: true,
    body: JSON.stringify({ role }),
  })
}

export function deleteUser(id_utilisateur: number): Promise<void> {
  return apiFetch<void>(`/users/${id_utilisateur}`, { method: 'DELETE', auth: true })
}
