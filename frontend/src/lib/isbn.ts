/**
 * ISBN helpers shared by the scan flow and the admin book form.
 */

/**
 * Normalize a raw scanned/typed ISBN: keep only digits and the check char X,
 * uppercased. Shared by the scan page and the admin book-create page (was
 * duplicated in both).
 */
export function cleanIsbn(value: string): string {
  return value.replace(/[^0-9Xx]/g, '').toUpperCase()
}

function isValidIsbn13(digits: string): boolean {
  if (!/^\d{13}$/.test(digits)) return false
  let sum = 0
  for (let i = 0; i < 12; i++) sum += Number(digits[i]) * (i % 2 === 0 ? 1 : 3)
  return (10 - (sum % 10)) % 10 === Number(digits[12])
}

function isValidIsbn10(value: string): boolean {
  if (!/^\d{9}[\dX]$/.test(value)) return false
  let sum = 0
  for (let i = 0; i < 9; i++) sum += Number(value[i]) * (10 - i)
  sum += value[9] === 'X' ? 10 : Number(value[9])
  return sum % 11 === 0
}

/**
 * True when `value` is a real ISBN: a 13-digit EAN in the Bookland prefixes
 * (978/979) with a valid check digit, or a valid ISBN-10.
 *
 * The barcode scanner reads whatever barcode is in frame, and a second-hand
 * book very often carries more than one: a shop price sticker, a library or
 * inventory label, a UPC on shrink-wrap. Those decode fine as EAN-13/UPC-A, so
 * without this check the scanner would happily "find" a non-book number, send
 * it to OpenLibrary (no result) and leave the volunteer with a silently wrong
 * ISBN pre-filled in the form. Checking the prefix and the check digit rejects
 * those, and also catches a plain misread.
 */
export function isValidIsbn(value: string): boolean {
  const clean = cleanIsbn(value)
  if (clean.length === 13) return /^97[89]/.test(clean) && isValidIsbn13(clean)
  if (clean.length === 10) return isValidIsbn10(clean)
  return false
}
