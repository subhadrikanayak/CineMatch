import { useEffect, useState } from 'react'
import { X } from 'lucide-react'
import { errorMessage } from '../api/client.js'
import { moviesTogether, searchPeople } from '../api/browse.js'
import ActorPicker from '../components/ActorPicker.jsx'
import Avatar, { PersonTile } from '../components/Avatar.jsx'
import Chip from '../components/Chip.jsx'
import MovieCard from '../components/MovieCard.jsx'
import Spinner from '../components/Spinner.jsx'

const GENDERS = [['', 'Everyone'], ['male', 'Actors'], ['female', 'Actresses']]

export default function People() {
  const [q, setQ] = useState('')
  const [gender, setGender] = useState('')
  const [results, setResults] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const [pair, setPair] = useState([null, null])
  const [together, setTogether] = useState(null)
  const [tBusy, setTBusy] = useState(false)
  const [tError, setTError] = useState('')

  useEffect(() => {
    if (q.trim().length < 2) {
      setResults(null)
      return
    }
    let cancelled = false
    setBusy(true)
    setError('')
    const t = setTimeout(() => {
      searchPeople(q.trim(), gender)
        .then((r) => !cancelled && setResults(r))
        .catch((e) => !cancelled && setError(errorMessage(e)))
        .finally(() => !cancelled && setBusy(false))
    }, 300)
    return () => { cancelled = true; clearTimeout(t) }
  }, [q, gender])

  useEffect(() => {
    setTogether(null)
    setTError('')
    if (!pair[0] || !pair[1]) return
    let cancelled = false
    setTBusy(true)
    moviesTogether(pair[0].id, pair[1].id)
      .then((r) => !cancelled && setTogether(r))
      .catch((e) => !cancelled && setTError(errorMessage(e)))
      .finally(() => !cancelled && setTBusy(false))
    return () => { cancelled = true }
  }, [pair])

  const setSlot = (i) => (person) => {
    const other = pair[1 - i]
    if (other && other.id === person.id) return setTError('Choose two different people.')
    setTError('')
    setPair((p) => p.map((x, idx) => (idx === i ? person : x)))
  }
  const clearSlot = (i) => setPair((p) => p.map((x, idx) => (idx === i ? null : x)))

  return (
    <div className="container-page py-10">
      <h1 className="text-3xl">Actors and actresses</h1>
      <p className="mt-2 text-mute">Search for someone, then open their filmography.</p>

      <div className="mt-6 max-w-xl">
        <input className="input" value={q} onChange={(e) => setQ(e.target.value)}
          placeholder="Type at least 2 letters, e.g. Mohan" />
        <div className="mt-3 flex gap-2">
          {GENDERS.map(([v, l]) => (
            <Chip key={v} active={gender === v} onClick={() => setGender(v)}>{l}</Chip>
          ))}
        </div>
      </div>

      {error && <p className="card mt-4 p-4 text-sm text-red-300">{error}</p>}
      {busy && <Spinner label="Searching" />}
      {results && !busy && (
        results.length === 0 ? (
          <p className="mt-6 text-mute">No one found. Only cast of movies in the catalogue is searchable.</p>
        ) : (
          <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {results.map((p) => <PersonTile key={p.id} person={p} />)}
          </div>
        )
      )}

      <section className="mt-14">
        <h2 className="text-2xl">Movies together</h2>
        <p className="mt-1 text-sm text-mute">Pick two people to see the movies that feature both.</p>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {[0, 1].map((i) => (
            <div key={i} className="card p-4">
              <p className="mb-2 text-xs uppercase tracking-wide text-mute">Person {i + 1}</p>
              {pair[i] ? (
                <div className="flex items-center gap-3">
                  <Avatar url={pair[i].profile_url} name={pair[i].name} />
                  <span className="flex-1 text-ink">{pair[i].name}</span>
                  <button onClick={() => clearSlot(i)} aria-label="Remove" className="text-mute hover:text-gold">
                    <X size={16} />
                  </button>
                </div>
              ) : (
                <ActorPicker onPick={setSlot(i)} />
              )}
            </div>
          ))}
        </div>

        {tError && <p className="mt-3 text-sm text-red-300">{tError}</p>}
        {tBusy && <Spinner label="Finding movies" />}
        {together && !tBusy && (
          <div className="mt-6">
            {together.items.length === 0 ? (
              <p className="card p-6 text-center text-mute">
                No movies in the catalogue feature both of them.
              </p>
            ) : (
              <>
                <p className="mb-3 text-sm text-mute">
                  {together.total} {together.total === 1 ? 'movie features' : 'movies feature'} both
                </p>
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
                  {together.items.map((m) => <MovieCard key={m.id} movie={m} />)}
                </div>
              </>
            )}
            <p className="mt-4 text-xs text-mute">
              Based on the top 15 billed cast of each movie in the catalogue.
            </p>
          </div>
        )}
      </section>
    </div>
  )
}