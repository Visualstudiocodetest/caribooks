'use client'

import { useEffect, useState } from 'react'

export function useLocalStorageState<T>(key: string, initialValue: T) {
  const [value, setValue] = useState<T>(initialValue)
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(key)
      if (raw != null) setValue(JSON.parse(raw) as T)
    } catch {
      // ignore
    } finally {
      setHydrated(true)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  useEffect(() => {
    if (!hydrated) return
    try {
      window.localStorage.setItem(key, JSON.stringify(value))
    } catch {
      // ignore
    }
  }, [hydrated, key, value])

  // Cross-tab sync: reflect changes made in other tabs (e.g. logging out or
  // editing the cart elsewhere) instead of leaving this tab stale.
  useEffect(() => {
    function onStorage(e: StorageEvent) {
      if (e.key !== key) return
      try {
        setValue(e.newValue != null ? (JSON.parse(e.newValue) as T) : initialValue)
      } catch {
        // ignore malformed values
      }
    }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  return { value, setValue, hydrated }
}
