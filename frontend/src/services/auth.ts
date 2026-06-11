import { apiFetch } from './api'
import type { LoginRequest, Token, UserCreate, UserRead } from '@/types/api'

export async function login(payload: LoginRequest): Promise<Token> {
  return apiFetch<Token>('/auth/token', { method: 'POST', body: JSON.stringify(payload), auth: true })
}

export async function register(payload: UserCreate): Promise<UserRead> {
  return apiFetch<UserRead>('/auth/register', { method: 'POST', body: JSON.stringify(payload), auth: true })
}

export function getCurrentUser(): Promise<UserRead> {
  return apiFetch<UserRead>('/users/me', { auth: true })
}

export function updateCurrentUser(payload: Partial<UserCreate & { mot_de_passe?: string }>): Promise<UserRead> {
  return apiFetch<UserRead>('/users/me', { method: 'PUT', auth: true, body: JSON.stringify(payload) })
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
