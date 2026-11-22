import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Bookmark, Check, Film, Star, ThumbsDown, ThumbsUp, User as UserIcon } from 'lucide-react'
import { errorMessage } from '../api/client.js'
import { getMovie, similarMovies } from '../api/movies.js'
import * as userApi from '../api/user.js'
import MovieCard from '../components/MovieCard.jsx'
import RatingStars from '../components/RatingStars.jsx'
import Spinner from '../components/Spinner.jsx'
import Comments from '../components/Comments.jsx'
import { useAuth } from '../context/AuthContext.jsx'

const OFFER = { flatrate: 'Stream', rent: 'Rent', buy: 'Buy', free: 'Free', ads: 'Free with ads' }

const runtimeText = (m) => (m ? `${Math.floor(m / 60)}h ${m % 60}m` : null)

function ActionButton({ active, icon: Icon, children, ...props }) {
  return (
    <button {...props}
      className={`btn-ghost gap-2 ${active ? 'border-gold text-gold' : ''}`}>
      <Icon size={15} /> {children}
    </button>
  )
}

export default function MovieDetail() {
  const { id } = useParams()
  const { user } = useAuth()
  const navigate = useNavigate()
  const [movie, setMovie] = useState(null)
  const [similar, setSimilar] = useState([])
  const [state, setState] = useState(null)
  const [error, setError] = useState('')
  const [note, setNote] = useState('')

  useEffect(() => {
    let cancelled = false
    setMovie(null); setSimilar([]); setError('')
    getMovie(id)
      .then((m) => !cancelled && setMovie(m))
      .catch((e) => !cancelled && setError(errorMessage(e)))
    similarMovies(id, 8).then((s) => !cancelled && setSimilar(s)).catch(() => {})
    window.scrollTo({ top: 0 })
    return () => { cancelled = true }
  }, [id])

  useEffect(() => {
    setState(null)
    if (user) userApi.movieState(id).then(setState).catch(() => {})
  }, [id, user])

  const run = async (fn) => {
    if (!user) return navigate('/login', { state: { from: `/movies/${id}` } })
    setNote('')
    try {
      await fn()
      setState(await userApi.movieState(id))
    } catch (e) {
      setNote(errorMessage(e))
    }
  }

  if (error) return <div className="container-page py-16 text-center text-mute">{error}</div>
  if (!movie) return <Spinner label="Loading movie" />

  const groups = {}
  movie.streaming.forEach((s) => (groups[s.offer_type] ||= []).push(s))
  const meta = [movie.release_year, movie.language, runtimeText(movie.runtime)].filter(Boolean)

  return (
    <div>
      {movie.backdrop_url && (
        <div className="relative h-56 overflow-hidden sm:h-72">
          <img src={movie.backdrop_url} alt="" className="h-full w-full object-cover opacity-30" />
          <div className="absolute inset-0 bg-gradient-to-t from-canvas to-transparent" />
        </div>
      )}

      <div className={`container-page ${movie.backdrop_url ? '-mt-32 relative' : 'pt-10'}`}>
        <div className="grid gap-8 md:grid-cols-[260px_1fr]">
          <div className="mx-auto w-56 md:w-full">
            <div className="aspect-[2/3] overflow-hidden rounded-xl border border-line bg-black/20 shadow-soft">
              {movie.poster_url
                ? <img src={movie.poster_url} alt={`${movie.title} poster`} className="h-full w-full object-cover" />
                : <div className="flex h-full items-center justify-center text-mute/40"><Film size={48} /></div>}
            </div>
          </div>

          <div>
            <h1 className="text-3xl sm:text-4xl">{movie.title}</h1>
            {movie.original_title && movie.original_title !== movie.title && (
              <p className="mt-1 text-sm text-mute">{movie.original_title}</p>
            )}
            <p className="mt-2 text-sm text-mute">{meta.join(' · ')}</p>

            <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
              <span className="flex items-center gap-1">
                <Star size={16} className="text-gold" fill="currentColor" />
                {movie.rating != null ? (
                  <>
                    <b>{movie.rating.toFixed(1)}</b>
                    <span className="text-mute">
                      {movie.rating_source?.toUpperCase()}
                      {movie.votes != null && ` · ${movie.votes.toLocaleString()} votes`}
                    </span>
                  </>
                ) : <span className="text-mute">No rating yet</span>}
              </span>
              {movie.genres.map((g) => (
                <Link key={g} to={`/discover?genre=${encodeURIComponent(g)}`}
                  className="rounded-full border border-line px-3 py-0.5 text-xs text-mute hover:border-gold-dim hover:text-gold">
                  {g}
                </Link>
              ))}
            </div>

            {movie.dubbed_languages && (
              <p className="mt-2 text-xs text-mute">Dubbed: {movie.dubbed_languages}</p>
            )}

            <p className="mt-5 max-w-3xl leading-relaxed text-ink/90">
              {movie.overview || 'No description available.'}
            </p>

            {movie.directors.length > 0 && (
              <p className="mt-4 text-sm text-mute">
                Directed by <span className="text-ink">{movie.directors.map((d) => d.name).join(', ')}</span>
              </p>
            )}

            <div className="card mt-6 space-y-4 p-4">
              <div className="flex flex-wrap items-center gap-4">
                <div>
                  <p className="mb-1 text-xs uppercase tracking-wide text-mute">Your rating</p>
                  <RatingStars value={state?.rating}
                    onChange={(v) => run(() => userApi.rateMovie(id, v))} />
                </div>
                {state?.rating != null && (
                  <button className="text-xs text-mute underline hover:text-gold"
                    onClick={() => run(() => userApi.unrateMovie(id))}>
                    Clear rating
                  </button>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                <ActionButton icon={Bookmark} active={state?.in_watchlist}
                  onClick={() => run(() => state?.in_watchlist ? userApi.removeWatchlist(id) : userApi.addWatchlist(id))}>
                  {state?.in_watchlist ? 'In watchlist' : 'Add to watchlist'}
                </ActionButton>
                <ActionButton icon={Check} active={state?.watched}
                  onClick={() => run(() => state?.watched ? userApi.unmarkWatched(id) : userApi.markWatched(id))}>
                  {state?.watched ? 'Watched' : 'Mark as watched'}
                </ActionButton>
                <ActionButton icon={ThumbsUp} active={state?.reaction === 'like'}
                  onClick={() => run(() => state?.reaction === 'like' ? userApi.clearReaction(id) : userApi.react(id, 'like'))}>
                  Like
                </ActionButton>
                <ActionButton icon={ThumbsDown} active={state?.reaction === 'dislike'}
                  onClick={() => run(() => state?.reaction === 'dislike' ? userApi.clearReaction(id) : userApi.react(id, 'dislike'))}>
                  Dislike
                </ActionButton>
              </div>
              {!user && (
                <p className="text-xs text-mute">
                  <Link to="/login" state={{ from: `/movies/${id}` }} className="text-gold hover:underline">Log in</Link>{' '}
                  to rate, save and get better recommendations.
                </p>
              )}
              {note && <p className="text-sm text-red-300">{note}</p>}
            </div>

            <div className="mt-6">
              <h2 className="text-xl">Where to watch (India)</h2>
              {movie.streaming.length === 0 ? (
                <p className="mt-2 text-sm text-mute">
                  No verified streaming data for this movie. It may still be available somewhere;
                  we only show what TMDB confirms.
                </p>
              ) : (
                <div className="mt-3 space-y-3">
                  {Object.entries(groups).map(([type, list]) => (
                    <div key={type} className="flex flex-wrap items-center gap-3">
                      <span className="w-28 text-xs uppercase tracking-wide text-mute">{OFFER[type] || type}</span>
                      {list.map((s) => (
                        <span key={s.provider} className="flex items-center gap-2 rounded-lg border border-line px-2 py-1 text-sm">
                          {s.logo_url && <img src={s.logo_url} alt="" className="h-5 w-5 rounded" />}
                          {s.provider}
                        </span>
                      ))}
                    </div>
                  ))}
                  <p className="text-xs text-mute">Streaming data provided via TMDB (powered by JustWatch).</p>
                </div>
              )}
            </div>

            {movie.keywords.length > 0 && (
              <div className="mt-6 flex flex-wrap gap-2">
                {movie.keywords.slice(0, 12).map((k) => (
                  <span key={k} className="rounded-full bg-white/5 px-3 py-1 text-xs text-mute">{k}</span>
                ))}
              </div>
            )}
          </div>
        </div>

        {movie.cast.length > 0 && (
          <section className="mt-12">
            <h2 className="text-2xl">Cast</h2>
            <div className="mt-4 grid grid-cols-3 gap-4 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8">
              {movie.cast.slice(0, 16).map((c) => (
                <Link key={c.id} to={`/people/${c.id}`} className="group text-center">
                  <div className="mx-auto aspect-square w-full overflow-hidden rounded-full border border-line bg-black/20">
                    {c.profile_url
                      ? <img src={c.profile_url} alt={c.name} loading="lazy" className="h-full w-full object-cover" />
                      : <div className="flex h-full items-center justify-center text-mute/40"><UserIcon size={28} /></div>}
                  </div>
                  <p className="mt-2 line-clamp-1 text-xs text-ink group-hover:text-gold">{c.name}</p>
                  {c.character && <p className="line-clamp-1 text-xs text-mute">{c.character}</p>}
                </Link>
              ))}
            </div>
          </section>
        )}

        {similar.length > 0 && (
          <section className="mt-12">
            <h2 className="text-2xl">Similar movies</h2>
            <p className="mt-1 text-sm text-mute">Matched on genres, cast, directors, keywords and description.</p>
            <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
              {similar.map((s) => {
                const why = [
                  s.shared_genres.length && `Shared genres: ${s.shared_genres.join(', ')}`,
                  s.shared_cast.length && `Shared cast: ${s.shared_cast.slice(0, 2).join(', ')}`,
                  s.same_director && 'Same director',
                ].filter(Boolean).join(' · ')
                return <MovieCard key={s.movie.id} movie={s.movie} reason={why || undefined} />
              })}
            </div>
          </section>
        )}
        <Comments movieId={id} />
      </div>
    </div>
  )
}