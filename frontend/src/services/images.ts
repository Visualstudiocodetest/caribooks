import { apiFetch } from './api'

export async function fetchRemoteImage(url: string): Promise<string> {
  const res = await apiFetch<{ image_link: string }>('/images/fetch', {
    method: 'POST',
    body: JSON.stringify({ url }),
  })
  return res.image_link
}
