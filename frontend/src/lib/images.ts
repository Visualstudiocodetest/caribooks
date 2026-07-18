/**
 * True when `src` points to an external image (an absolute http(s) URL that is
 * NOT already served from our own /static/images folder). Used to decide when to
 * pass `unoptimized` to next/image. Previously this test was copy-pasted in 5+
 * components.
 */
export function isExternalImage(src: string | null | undefined): boolean {
  return Boolean(src && src.startsWith('http') && !src.includes('/static/images/'))
}
