import { useEffect, useState } from 'react'

// Runs fn() when deps change. Returns { data, error, loading, reload }.
export default function useLoad(fn, deps = []) {
  const [s, setS] = useState({ data: null, error: '', loading: true })
  const [tick, setTick] = useState(0)

  useEffect(() => {
    let cancelled = false
    setS((p) => ({ ...p, loading: true, error: '' }))
    fn()
      .then((data) => !cancelled && setS({ data, error: '', loading: false }))
      .catch((e) => {
        if (cancelled) return
        const d = e.response?.data?.detail
        setS({ data: null, loading: false,
          error: typeof d === 'string' ? d : e.message || 'Something went wrong' })
      })
    return () => { cancelled = true }
  }, [...deps, tick]) // eslint-disable-line

  return { ...s, reload: () => setTick((t) => t + 1) }
}