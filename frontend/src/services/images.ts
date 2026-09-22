import { apiFetch } from './api'

export async function fetchRemoteImage(url: string): Promise<string> {
  const res = await apiFetch<{ image_link: string }>('/images/fetch', {
    method: 'POST',
    auth: true,
    body: JSON.stringify({ url }),
  })
  return res.image_link
}

export async function uploadLocalImage(file: File): Promise<string> {
  const form = new FormData()
  form.append('file', file)
  const res = await apiFetch<{ image_link: string }>('/images/upload', {
    method: 'POST',
    auth: true,
    body: form,
  })
  return res.image_link
}
