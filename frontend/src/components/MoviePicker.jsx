import { useEffect, useState } from 'react'
import { Search } from 'lucide-react'
import { quickSearch } from '../api/browse.js'

export default function MoviePicker({ onPick, placeholder = 'Search a movie' }) {
  const [q, setQ] = useState('')
  const [results, setResults] = useState([])
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (q.trim().length < 2) {
      setResults([])
      return
    }
    let cancelled = false
    setBusy(true)
    const t = setTimeout(() => {
      quickSearch(q.trim(), 8)
        .then((r) => !cancelled && setResults(r.movies))
        .catch(() => !cancelled && setResults([]))
        .finally(() => !cancelled && setBusy(false))
    }, 300)
    return () => { cancelled = true; clearTimeout(t) }
  }, [q])

  const pick = (m) => {
    onPick(m)
    setQ('')
    setResults([])
  }

  return (
    <div className="relative">
      <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-mute" />
      <input className="input pl-9" value={q} placeholder={placeholder}
        onChange={(e) => setQ(e.target.value)} />
      {q.trim().length >= 2 && (
        <div className="absolute z-30 mt-1 max-h-72 w-full overflow-auto rounded-xl border border-line bg-raised p-1 shadow-soft backdrop-blur-md">
          {busy && <p className="p-3 text-xs text-mute">Searching...</p>}
          {!busy && results.length === 0 && <p className="p-3 text-xs text-mute">No movies found.</p>}
          {results.map((m) => (
            <button key={m.id} type="button" onClick={() => pick(m)}
              className="block w-full rounded-lg p-2 text-left hover:bg-white/10">
              <span className="text-sm text-ink">{m.title}</span>
              <span className="ml-2 text-xs text-mute">
                {[m.release_year, m.language].filter(Boolean).join(' · ')}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}