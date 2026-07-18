import { apiFetch } from './api'
import type { LoginRequest, Token, UserCreate, UserRead } from '@/types/api'

// login/register are credential exchanges — they must NOT attach any existing
// bearer token (auth: false). Sending a stale token with the login body served
// no purpose and needlessly exposed it.
export async function login(payload: LoginRequest): Promise<Token> {
  return apiFetch<Token>('/auth/token', { method: 'POST', body: JSON.stringify(payload) })
}

export async function register(payload: UserCreate): Promise<UserRead> {
  return apiFetch<UserRead>('/auth/register', { method: 'POST', body: JSON.stringify(payload) })
}

export function getCurrentUser(): Promise<UserRead> {
  return apiFetch<UserRead>('/users/me', { auth: true })
}

export function updateCurrentUser(payload: Partial<UserCreate & { mot_de_passe?: string }>): Promise<UserRead> {
  return apiFetch<UserRead>('/users/me', { method: 'PUT', auth: true, body: JSON.stringify(payload) })
}

// RGPD / nLPD — droit à la portabilité : export des données personnelles
export function exportMyData(): Promise<unknown> {
  return apiFetch<unknown>('/users/me/export', { auth: true })
}

// RGPD / nLPD — droit à l'effacement : suppression (anonymisation) du compte
export function deleteMyAccount(): Promise<void> {
  return apiFetch<void>('/users/me', { method: 'DELETE', auth: true })
}

export async function googleLogin(credential: string): Promise<Token> {
  return apiFetch<Token>('/auth/google', { method: 'POST', body: JSON.stringify({ credential }) })
}

export function persistToken(token: string) {
  window.localStorage.setItem('caribooks_token', JSON.stringify(token))
}

export function clearToken() {
  window.localStorage.removeItem('caribooks_token')
}

export function readToken(): string | null {
  const raw = window.localStorage.getItem('caribooks_token')
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw) as unknown
    return typeof parsed === 'string' ? parsed : raw
  } catch {
    return raw
  }
}
