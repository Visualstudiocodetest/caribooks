import { apiFetch } from './api'
import type { ScanISBNCreate, ScanISBNRead } from '@/types/api'

export function createScan(payload: ScanISBNCreate): Promise<ScanISBNRead> {
  return apiFetch<ScanISBNRead>('/scans/', { method: 'POST', auth: true, body: JSON.stringify(payload) })
}

export function listScans(): Promise<ScanISBNRead[]> {
  return apiFetch<ScanISBNRead[]>('/scans/', { auth: true })
}
