import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { errorMessage } from '../api/client.js'
import { getPerson, personMovies } from '../api/browse.js'
import { filterOptions } from '../api/movies.js'
import Avatar from '../components/Avatar.jsx'
import LanguageChips from '../components/LanguageChips.jsx'
import MovieCard from '../components/MovieCard.jsx'
import Pagination from '../components/Pagination.jsx'
import Spinner from '../components/Spinner.jsx'

const EMPTY = { language: [], genre: '', min_rating: '', year_min: '', year_max: '', sort: 'popularity' }
const num = (v) => (v === '' ? undefined : Number(v))
const ROLE = { male: 'Actor', female: 'Actress' }

export default function PersonDetail() {
  const { id } = useParams()
  const [person, setPerson] = useState(null)
  const [options, setOptions] = useState(null)
  const [f, setF] = useState(EMPTY)
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => { filterOptions().then(setOptions).catch(() => {}) }, [])

  useEffect(() => {
    setPerson(null); setF(EMPTY); setPage(1); setError('')
    getPerson(id).then(setPerson).catch((e) => setError(errorMessage(e)))
  }, [id])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    personMovies(id, {
      language: f.language.length ? f.language : undefined,
      genre: f.genre || undefined,
      min_rating: num(f.min_rating), year_min: num(f.year_min), year_max: num(f.year_max),
      sort: f.sort, page, page_size: 24,
    })
      .then((d) => !cancelled && (setData(d), setError('')))
      .catch((e) => !cancelled && setError(errorMessage(e)))
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [id, f, page])

  const update = (patch) => { setF((p) => ({ ...p, ...patch })); setPage(1) }
  const set = (k) => (e) => update({ [k]: e.target.value })

  if (error && !person) return <div className="container-page py-16 text-center text-mute">{error}</div>
  if (!person) return <Spinner label="Loading" />

  return (
    <div className="container-page py-10">
      <div className="flex items-center gap-5">
        <Avatar url={person.profile_url} name={person.name} size="h-24 w-24" />
        <div>
          <h1 className="text-3xl">{person.name}</h1>
          <p className="mt-1 text-sm text-mute">
            {ROLE[person.gender] || 'Cast'} · {person.movie_count} {person.movie_count === 1 ? 'movie' : 'movies'} in the catalogue
          </p>
        </div>
      </div>

      <div className="card mt-8 space-y-4 p-4">
        <LanguageChips value={f.language} onChange={(language) => update({ language })} />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <select className="input" value={f.genre} onChange={set('genre')}>
            <option value="">Any genre</option>
            {(options?.genres || []).map((g) => <option key={g}>{g}</option>)}
          </select>
          <select className="input" value={f.min_rating} onChange={set('min_rating')}>
            <option value="">Any rating</option>
            {[5, 6, 7, 8].map((r) => <option key={r} value={r}>{r}+</option>)}
          </select>
          <input className="input" type="number" placeholder="Year from" value={f.year_min} onChange={set('year_min')} />
          <input className="input" type="number" placeholder="Year to" value={f.year_max} onChange={set('year_max')} />
          <select className="input" value={f.sort} onChange={set('sort')}>
            <option value="popularity">Popularity</option>
            <option value="rating">Rating</option>
            <option value="year">Newest</option>
            <option value="title">Title A to Z</option>
          </select>
        </div>
        <button className="btn-ghost" onClick={() => { setF(EMPTY); setPage(1) }}>Reset filters</button>
      </div>

      {error && <p className="card mt-4 p-4 text-sm text-red-300">{error}</p>}
      {loading && <Spinner label="Loading filmography" />}
      {data && !loading && (
        <>
          <p className="mb-3 mt-6 text-sm text-mute">{data.total} {data.total === 1 ? 'movie' : 'movies'}</p>
          {data.items.length === 0 ? (
            <p className="card p-6 text-center text-mute">No movies match these filters.</p>
          ) : (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
              {data.items.map((m) => <MovieCard key={m.id} movie={m} />)}
            </div>
          )}
          <Pagination page={page} pages={data.pages} onChange={(n) => { setPage(n); window.scrollTo({ top: 0 }) }} />
        </>
      )}
    </div>
  )
}