import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Dices, Search, SlidersHorizontal, Sparkles } from 'lucide-react'
import { errorMessage } from '../api/client.js'
import { filterOptions, listMovies, semanticSearch, surprise } from '../api/movies.js'
import FilterSidebar from '../components/FilterSidebar.jsx'
import MovieCard from '../components/MovieCard.jsx'
import Pagination from '../components/Pagination.jsx'
import Spinner from '../components/Spinner.jsx'
import { useAuth } from '../context/AuthContext.jsx'

const num = (v) => (v === '' || v == null ? undefined : Number(v))
const arr = (a) => (a.length ? a : undefined)

function filtersFrom(p) {
  return {
    language: p.getAll('language'),
    genre: p.getAll('genre'),
    genre_match: p.get('genre_match') || 'any',
    min_rating: num(p.get('min_rating')),
    year_min: num(p.get('year_min')),
    year_max: num(p.get('year_max')),
    runtime_max: num(p.get('runtime_max')),
  }
}

export default function Discover() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const [options, setOptions] = useState(null)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [text, setText] = useState(params.get('q') || '')
  const [showFilters, setShowFilters] = useState(false)

  const smart = params.get('smart') === '1'
  const page = Number(params.get('page') || 1)
  const key = params.toString()

  useEffect(() => {
    filterOptions().then(setOptions).catch(() => {})
  }, [])

  useEffect(() => {
    setText(params.get('q') || '')
    let cancelled = false
    const f = filtersFrom(params)
    const q = (params.get('q') || '').trim()
    setLoading(true)
    setError('')

    const request =
      smart && q
        ? semanticSearch({
            query: q, languages: f.language, genres: f.genre, genre_match: f.genre_match,
            min_rating: f.min_rating, year_min: f.year_min, year_max: f.year_max,
            runtime_max: f.runtime_max, k: 30,
          }).then((r) => ({
            items: r.items.map((i) => ({ movie: i.movie, match: i.match_percent, reason: i.reasons.join(' · ') })),
            total: r.items.length, pages: 1,
            semantic: { parsed: r.parsed, note: r.note },
          }))
        : listMovies({
            language: arr(f.language), genre: arr(f.genre), genre_match: f.genre_match,
            min_rating: f.min_rating, year_min: f.year_min, year_max: f.year_max,
            runtime_max: f.runtime_max, q: q || undefined,
            sort: params.get('sort') || 'popularity', page, page_size: 24,
          }).then((r) => ({
            items: r.items.map((m) => ({ movie: m })), total: r.total, pages: r.pages,
          }))

    request
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && (setError(errorMessage(e)), setData(null)))
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [key]) // eslint-disable-line

  const applyFilters = (f) => {
    const p = new URLSearchParams()
    if (params.get('q')) p.set('q', params.get('q'))
    if (smart) p.set('smart', '1')
    f.language.forEach((l) => p.append('language', l))
    f.genre.forEach((g) => p.append('genre', g))
    if (f.genre_match !== 'any') p.set('genre_match', f.genre_match)
    ;['min_rating', 'year_min', 'year_max', 'runtime_max'].forEach((k) => f[k] && p.set(k, f[k]))
    if (f.sort !== 'popularity') p.set('sort', f.sort)
    setParams(p)
    setShowFilters(false)
  }

  const submit = (e) => {
    e.preventDefault()
    const p = new URLSearchParams(params)
    p.delete('page')
    text.trim() ? p.set('q', text.trim()) : p.delete('q')
    setParams(p)
  }

  const toggleSmart = () => {
    const p = new URLSearchParams(params)
    smart ? p.delete('smart') : p.set('smart', '1')
    p.delete('page')
    setParams(p)
  }

  const goToPage = (n) => {
    const p = new URLSearchParams(params)
    p.set('page', n)
    setParams(p)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const surpriseMe = async (outside) => {
    const f = filtersFrom(params)
    try {
      const r = await surprise({
        languages: f.language, genres: f.genre, genre_match: f.genre_match,
        min_rating: f.min_rating, year_min: f.year_min, year_max: f.year_max,
        runtime_max: f.runtime_max, outside_comfort_zone: outside,
      })
      navigate(`/movies/${r.movie.id}`)
    } catch (e) {
      setError(errorMessage(e))
    }
  }

  return (
    <div className="container-page py-10">
      <h1 className="text-3xl">Discover</h1>

      <form onSubmit={submit} className="mt-5 flex flex-wrap gap-2">
        <div className="relative min-w-[220px] flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-mute" />
          <input className="input pl-9" value={text} onChange={(e) => setText(e.target.value)}
            placeholder={smart ? 'Describe it, e.g. Malayalam psychological thriller with a twist'
              : 'Search title, keyword or description'} />
        </div>
        <button className="btn-primary">Search</button>
        <button type="button" onClick={toggleSmart}
          className={`btn-ghost gap-2 ${smart ? 'border-gold text-gold' : ''}`}>
          <Sparkles size={15} /> Smart search
        </button>
        <button type="button" className="btn-ghost gap-2 lg:hidden" onClick={() => setShowFilters((s) => !s)}>
          <SlidersHorizontal size={15} /> Filters
        </button>
      </form>

      <div className="mt-3 flex flex-wrap gap-2">
        <button className="btn-ghost gap-2" onClick={() => surpriseMe(false)}>
          <Dices size={15} /> Surprise me
        </button>
        {user && (
          <button className="btn-ghost" onClick={() => surpriseMe(true)}>
            Outside my comfort zone
          </button>
        )}
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-[270px_1fr]">
        <aside className={showFilters ? 'block' : 'hidden lg:block'}>
          <FilterSidebar options={options} params={params} onApply={applyFilters} />
        </aside>

        <section>
          {error && <p className="card p-4 text-sm text-red-300">{error}</p>}
          {loading && <Spinner label="Finding movies" />}

          {!loading && data && (
            <>
              <p className="mb-3 text-sm text-mute">
                {data.total} {data.total === 1 ? 'movie' : 'movies'}
              </p>
              {data.semantic && (
                <div className="card mb-4 p-3 text-xs text-mute">
                  <p>
                    Understood as filters: {[
                      ...data.semantic.parsed.languages, ...data.semantic.parsed.genres,
                    ].join(', ') || 'none'}
                    {data.semantic.parsed.description_text
                      && ` | matching description: "${data.semantic.parsed.description_text}"`}
                  </p>
                  {data.semantic.note && <p className="mt-1">{data.semantic.note}</p>}
                </div>
              )}
              {data.items.length === 0 ? (
                <p className="card p-6 text-center text-mute">
                  No movies match these filters. Try removing one.
                </p>
              ) : (
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4">
                  {data.items.map((i) => (
                    <MovieCard key={i.movie.id} movie={i.movie} match={i.match} reason={i.reason} />
                  ))}
                </div>
              )}
              <Pagination page={page} pages={data.pages} onChange={goToPage} />
            </>
          )}
        </section>
      </div>
    </div>
  )
}