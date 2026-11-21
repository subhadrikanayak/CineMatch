import { useEffect, useState } from 'react'
import { errorMessage } from '../api/client.js'
import { listMoods, moodRecommend } from '../api/movies.js'
import LanguageChips from '../components/LanguageChips.jsx'
import MovieCard from '../components/MovieCard.jsx'
import Spinner from '../components/Spinner.jsx'

export default function Moods() {
  const [moods, setMoods] = useState([])
  const [mood, setMood] = useState(null)
  const [langs, setLangs] = useState([])
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    listMoods().then(setMoods).catch((e) => setError(errorMessage(e)))
  }, [])

  useEffect(() => {
    if (!mood) return
    let cancelled = false
    setLoading(true)
    setError('')
    moodRecommend({ mood, languages: langs, k: 18 })
      .then((r) => !cancelled && setResult(r))
      .catch((e) => !cancelled && (setError(errorMessage(e)), setResult(null)))
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [mood, langs])

  return (
    <div className="container-page py-10">
      <h1 className="text-3xl">How are you feeling?</h1>
      <p className="mt-2 text-mute">Pick a mood and we rank movies by genre, keywords and description.</p>

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {moods.map((m) => (
          <button key={m.id} onClick={() => setMood(m.id)}
            className={`card p-4 text-left transition-colors hover:border-gold-dim ${
              mood === m.id ? 'border-gold' : ''}`}>
            <p className={`font-serif text-lg ${mood === m.id ? 'text-gold' : 'text-ink'}`}>{m.label}</p>
            <p className="mt-1 text-xs text-mute">{m.genres.join(', ')}</p>
          </button>
        ))}
      </div>

      <div className="mt-6">
        <p className="mb-2 text-xs uppercase tracking-wide text-mute">Language (optional)</p>
        <LanguageChips value={langs} onChange={setLangs} />
      </div>

      {error && <p className="card mt-6 p-4 text-sm text-red-300">{error}</p>}
      {loading && <Spinner label="Finding movies for your mood" />}

      {!mood && !loading && (
        <p className="mt-10 text-center text-mute">Choose a mood to see recommendations.</p>
      )}

      {result && !loading && (
        <section className="mt-8">
          {result.items.length === 0 ? (
            <p className="card p-6 text-center text-mute">No movies fit that mood with these filters.</p>
          ) : (
            <>
              <p className="mb-3 text-sm text-mute">
                {result.items.length} picks from {result.candidates} matching movies
              </p>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
                {result.items.map((r) => (
                  <MovieCard key={r.movie.id} movie={r.movie} match={r.match_percent} reason={r.reasons[0]} />
                ))}
              </div>
              <p className="mt-4 text-xs text-mute">{result.note}</p>
            </>
          )}
        </section>
      )}
    </div>
  )
}