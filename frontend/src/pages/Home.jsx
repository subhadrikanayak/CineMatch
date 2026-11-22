import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import { errorMessage } from '../api/client.js'
import { guestRecommendations, listMovies, myRecommendations } from '../api/movies.js'
import MovieCard from '../components/MovieCard.jsx'
import Spinner from '../components/Spinner.jsx'
import { useAuth } from '../context/AuthContext.jsx'

const LANGUAGES = [
  { code: 'hi', name: 'Hindi' },
  { code: 'te', name: 'Telugu' },
  { code: 'ta', name: 'Tamil' },
  { code: 'ml', name: 'Malayalam' },
  { code: 'kn', name: 'Kannada' },
]


const FEATURED = [
  ['meiyazhagan'],
  ['maharshi'],
  ['hi nanna'],
  ['12th fail'],
  ['baththa'],     
  ['irumudi'],    
]

function Section({ title, subtitle, children, more }) {
  return (
    <section className="container-page mt-8">
      <div className="flex items-end justify-between">
        <div>
          <h2 className="text-2xl text-ink">{title}</h2>
          {subtitle && <p className="mt-1 text-sm text-mute">{subtitle}</p>}
        </div>
        {more && (
          <Link to={more} className="text-sm text-gold hover:underline">See all</Link>
        )}
      </div>
      <div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
        {children}
      </div>
    </section>
  )
}

export default function Home() {
  const { user, loading: authLoading } = useAuth()
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [recs, setRecs] = useState(null)
  const [latest, setLatest] = useState(null)
  const [byLang, setByLang] = useState({})
  const [featured, setFeatured] = useState(null)
  const [error, setError] = useState('')

  // Recommendations depend on the logged-in user.
  useEffect(() => {
    if (authLoading) return
    let cancelled = false
    setError('')
    setRecs(null)
    const req = user ? myRecommendations({ k: 12 }) : guestRecommendations({ k: 12 })
    req
      .then((d) => !cancelled && setRecs(d))
      .catch((e) => !cancelled && setError(errorMessage(e)))
    return () => { cancelled = true }
  }, [user, authLoading])

  // Browse rows: same for everyone, loaded once.
  useEffect(() => {
    let cancelled = false
    listMovies({ sort: 'year', min_rating: 6.5, page_size: 6 })
      .then((d) => !cancelled && setLatest(d.items))
      .catch(() => {})
    LANGUAGES.forEach((l) => {
      listMovies({ language: [l.code], sort: 'popularity', page_size: 6 })
        .then((d) => !cancelled && setByLang((p) => ({ ...p, [l.code]: d.items })))
        .catch(() => {})
    })
    return () => { cancelled = true }
  }, [])

  // Featured row: look each film up by title. Only a real title match is accepted.
  useEffect(() => {
    let cancelled = false
    Promise.all(
      FEATURED.map(async (aliases) => {
        for (const name of aliases) {
          try {
            const d = await listMovies({ q: name, page_size: 10 })
            const hit = d.items.find((m) => m.title.toLowerCase().includes(name))
            if (hit) return hit
          } catch (e) { /* try the next spelling */ }
        }
        return null
      }),
    ).then((list) => !cancelled && setFeatured(list.filter(Boolean)))
    return () => { cancelled = true }
  }, [])

  const submit = (e) => {
    e.preventDefault()
    const term = q.trim()
    navigate(term ? `/discover?q=${encodeURIComponent(term)}` : '/discover')
  }

  return (
    <>
      <section className="border-b border-line">
        <div className="container-page py-10 text-center sm:py-12">
          <h1 className="text-4xl text-ink sm:text-5xl">
            Find your next <span className="text-gold">Indian film</span>
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-mute">
            Hindi, Telugu, Tamil, Malayalam and Kannada cinema, matched to your taste and
            explained.
          </p>

          <form onSubmit={submit} className="mx-auto mt-8 flex max-w-xl gap-2">
            <div className="relative flex-1">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-mute" />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search a title, keyword or description"
                className="input pl-9"
                aria-label="Search movies"
              />
            </div>
            <button className="btn-primary">Search</button>
          </form>

          <div className="mt-6 flex flex-wrap justify-center gap-2">
            {LANGUAGES.map((l) => (
              <Link
                key={l.code}
                to={`/discover?language=${l.code}`}
                className="rounded-full border border-line px-4 py-1.5 text-sm text-mute transition-colors hover:border-gold-dim hover:text-gold"
              >
                {l.name}
              </Link>
            ))}
          </div>
        </div>
      </section>

      {error && (
        <div className="container-page mt-8">
          <p className="rounded-lg border border-line bg-surface p-4 text-sm text-mute">{error}</p>
        </div>
      )}

      {featured && featured.length > 0 && (
        <Section title="Featured" subtitle="Hand-picked films to start with.">
          {featured.map((m) => <MovieCard key={m.id} movie={m} />)}
        </Section>
      )}

      {recs ? (
        <Section
          title={recs.personalised ? 'Recommended for you' : 'Popular picks'}
          subtitle={
            recs.personalised
              ? 'Ranked from your favourites, ratings and watchlist.'
              : 'Log in, set favourites and rate a few movies to personalise this list.'
          }
        >
          {recs.items.map((r) => (
            <MovieCard
              key={r.movie.id}
              movie={r.movie}
              match={recs.personalised ? r.match_percent : null}
              reason={r.reasons[0]}
            />
          ))}
        </Section>
      ) : (
        !error && <Spinner label="Loading recommendations" />
      )}

      {latest && latest.length > 0 && (
        <Section title="New releases" subtitle="Recent films rated 6.5 or higher." more="/discover?sort=year&min_rating=6.5">
          {latest.map((m) => <MovieCard key={m.id} movie={m} />)}
        </Section>
      )}

      {LANGUAGES.map((l) =>
        byLang[l.code]?.length ? (
          <Section key={l.code} title={`Popular in ${l.name}`} more={`/discover?language=${l.code}`}>
            {byLang[l.code].map((m) => <MovieCard key={m.id} movie={m} />)}
          </Section>
        ) : null,
      )}
    </>
  )
}