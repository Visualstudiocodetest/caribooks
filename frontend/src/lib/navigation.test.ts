import { describe, expect, it } from 'vitest'
import { safeReturnTo } from './navigation'

describe('safeReturnTo', () => {
  it('accepts same-origin relative paths', () => {
    expect(safeReturnTo('/account')).toBe('/account')
    expect(safeReturnTo('/admin/orders?tab=new')).toBe('/admin/orders?tab=new')
  })

  it('rejects absolute and protocol-relative URLs (open redirect)', () => {
    expect(safeReturnTo('https://evil.com')).toBe('/')
    expect(safeReturnTo('http://evil.com')).toBe('/')
    expect(safeReturnTo('//evil.com')).toBe('/')
    expect(safeReturnTo('/\\evil.com')).toBe('/')
  })

  it('rejects empty / control-char values and honours a custom fallback', () => {
    expect(safeReturnTo(null)).toBe('/')
    expect(safeReturnTo('')).toBe('/')
    expect(safeReturnTo('/foo\nbar')).toBe('/')
    expect(safeReturnTo(null, '/login')).toBe('/login')
  })
})
