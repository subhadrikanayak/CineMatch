import { useEffect, useState } from 'react'
import { Search } from 'lucide-react'
import { searchPeople } from '../api/browse.js'
import Avatar from './Avatar.jsx'

export default function ActorPicker({ onPick, gender, placeholder = 'Search an actor or actress' }) {
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
      searchPeople(q.trim(), gender)
        .then((r) => !cancelled && setResults(r))
        .catch(() => !cancelled && setResults([]))
        .finally(() => !cancelled && setBusy(false))
    }, 300)
    return () => { cancelled = true; clearTimeout(t) }
  }, [q, gender])

  const pick = (p) => {
    onPick(p)
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
          {!busy && results.length === 0 && <p className="p-3 text-xs text-mute">No one found.</p>}
          {results.map((p) => (
            <button key={p.id} type="button" onClick={() => pick(p)}
              className="flex w-full items-center gap-3 rounded-lg p-2 text-left hover:bg-white/10">
              <Avatar url={p.profile_url} name={p.name} size="h-9 w-9" />
              <span className="text-sm text-ink">{p.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}