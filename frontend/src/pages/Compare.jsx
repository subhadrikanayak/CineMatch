import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { X } from 'lucide-react'
import { errorMessage } from '../api/client.js'
import { compareMovies } from '../api/browse.js'
import MoviePicker from '../components/MoviePicker.jsx'
import Spinner from '../components/Spinner.jsx'

function Row({ label, a, b, winA, winB }) {
  return (
    <tr className="border-t border-line align-top">
      <th className="w-1/5 py-3 pr-3 text-left text-xs font-normal uppercase tracking-wide text-mute">{label}</th>
      <td className={`py-3 pr-3 text-sm ${winA ? 'font-medium text-gold' : 'text-ink'}`}>{a}</td>
      <td className={`py-3 text-sm ${winB ? 'font-medium text-gold' : 'text-ink'}`}>{b}</td>
    </tr>
  )
}

const rating = (m) =>
  m.rating != null
    ? `${m.rating.toFixed(1)} ${m.rating_source.toUpperCase()}${m.votes ? ` (${m.votes.toLocaleString()} votes)` : ''}`
    : 'No rating yet'
const runtime = (m) => (m.runtime ? `${Math.floor(m.runtime / 60)}h ${m.runtime % 60}m` : '-')

export default function Compare() {
  const [params, setParams] = useSearchParams()
  const a = params.get('a')
  const b = params.get('b')
  const [picks, setPicks] = useState({ a: null, b: null })
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    setData(null)
    setError('')
    if (!a || !b) return
    if (a === b) return setError('Choose two different movies.')
    let cancelled = false
    setLoading(true)
    compareMovies(a, b)
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && setError(errorMessage(e)))
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [a, b])

  const pick = (slot) => (m) => {
    setPicks((p) => ({ ...p, [slot]: m }))
    const p = new URLSearchParams(params)
    p.set(slot, m.id)
    setParams(p)
  }
  const clear = (slot) => {
    setPicks((p) => ({ ...p, [slot]: null }))
    const p = new URLSearchParams(params)
    p.delete(slot)
    setParams(p)
  }

  const title = (slot) => data?.[slot]?.title || picks[slot]?.title || `Movie #${params.get(slot)}`
  const sim = data?.content_similarity

  return (
    <div className="container-page py-10">
      <h1 className="text-3xl">Compare movies</h1>
      <p className="mt-2 text-mute">Pick two movies to see them side by side.</p>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        {['a', 'b'].map((slot, i) => (
          <div key={slot} className="card p-4">
            <p className="mb-2 text-xs uppercase tracking-wide text-mute">Movie {i + 1}</p>
            {params.get(slot) ? (
              <div className="flex items-center justify-between gap-3">
                <span className="text-ink">{title(slot)}</span>
                <button onClick={() => clear(slot)} aria-label="Remove" className="text-mute hover:text-gold">
                  <X size={16} />
                </button>
              </div>
            ) : (
              <MoviePicker onPick={pick(slot)} />
            )}
          </div>
        ))}
      </div>

      {error && <p className="card mt-6 p-4 text-sm text-red-300">{error}</p>}
      {loading && <Spinner label="Comparing" />}

      {data && !loading && (
        <div className="card mt-6 overflow-x-auto p-4">
          <table className="w-full min-w-[520px]">
            <thead>
              <tr>
                <th />
                {[data.a, data.b].map((m) => (
                  <th key={m.id} className="pb-4 pr-3 text-left align-top">
                    <Link to={`/movies/${m.id}`} className="flex items-start gap-3 hover:text-gold">
                      {m.poster_url && <img src={m.poster_url} alt="" className="h-24 w-16 rounded-lg object-cover" />}
                      <span className="font-serif text-lg font-normal">{m.title}</span>
                    </Link>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <Row label="Rating" a={rating(data.a)} b={rating(data.b)}
                winA={data.higher_rated === data.a.id} winB={data.higher_rated === data.b.id} />
              <Row label="Language" a={data.a.language} b={data.b.language} />
              <Row label="Genres" a={data.a.genres.join(', ') || '-'} b={data.b.genres.join(', ') || '-'} />
              <Row label="Release year" a={data.a.release_year || '-'} b={data.b.release_year || '-'} />
              <Row label="Runtime" a={runtime(data.a)} b={runtime(data.b)} />
              <Row label="Director" a={data.a.directors.join(', ') || '-'} b={data.b.directors.join(', ') || '-'} />
              <Row label="Popularity" a={data.a.popularity?.toFixed(1) ?? '-'} b={data.b.popularity?.toFixed(1) ?? '-'}
                winA={data.more_popular === data.a.id} winB={data.more_popular === data.b.id} />
            </tbody>
          </table>

          <div className="mt-5 space-y-1 border-t border-line pt-4 text-sm text-mute">
            <p>Shared genres: {data.shared_genres.length ? data.shared_genres.join(', ') : 'none'}</p>
            <p>Same language: {data.same_language ? 'yes' : 'no'}</p>
            {data.year_gap != null && <p>Released {data.year_gap} {data.year_gap === 1 ? 'year' : 'years'} apart</p>}
            {sim != null && (
              <p>Content similarity (genres, cast, director, keywords, description): {Math.round(sim * 100)}%</p>
            )}
            {data.warnings.map((w) => <p key={w} className="text-gold-soft">Note: {w}</p>)}
            <p className="pt-1 text-xs">Gold marks the higher value. Popularity is the TMDB popularity score.</p>
          </div>
        </div>
      )}
    </div>
  )
}