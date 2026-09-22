import { describe, expect, it } from 'vitest'
import { cleanIsbn, isValidIsbn } from './isbn'

describe('cleanIsbn', () => {
  it('keeps digits and the X check character', () => {
    expect(cleanIsbn('978-2-07-036822-8')).toBe('9782070368228')
    expect(cleanIsbn(' 2-07-036822-x ')).toBe('207036822X')
  })
})

describe('isValidIsbn', () => {
  it('accepts real ISBN-13s in the Bookland prefixes', () => {
    expect(isValidIsbn('9782070368228')).toBe(true)
    expect(isValidIsbn('978-2-07-036822-8')).toBe(true)
    expect(isValidIsbn('9791036300035')).toBe(true) // 979 prefix
  })

  it('accepts a valid ISBN-10, including an X check digit', () => {
    expect(isValidIsbn('0306406152')).toBe(true)
    expect(isValidIsbn('207036822X')).toBe(true) // check digit 10 is written X
  })

  it('rejects a wrong check digit (a misread scan)', () => {
    expect(isValidIsbn('9782070368229')).toBe(false)
    expect(isValidIsbn('0306406153')).toBe(false)
  })

  it('rejects a non-Bookland EAN-13', () => {
    // A shop price sticker or a product UPC decodes perfectly well as EAN-13;
    // only 978/979 are books, so these must not be taken for an ISBN. This one
    // has a valid EAN check digit and is still not a book.
    expect(isValidIsbn('4006381333931')).toBe(false)
  })

  it('rejects anything that is not 10 or 13 characters', () => {
    expect(isValidIsbn('')).toBe(false)
    expect(isValidIsbn('12345678')).toBe(false)
    expect(isValidIsbn('97820703682281')).toBe(false)
  })
})
