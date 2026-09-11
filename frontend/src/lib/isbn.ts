/**
 * Normalize a raw scanned/typed ISBN: keep only digits and the check char X,
 * uppercased. Shared by the scan page and the admin book-create page (was
 * duplicated in both).
 */
export function cleanIsbn(value: string): string {
  return value.replace(/[^0-9Xx]/g, '').toUpperCase()
}
