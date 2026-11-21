import { useState } from 'react'
import { Link } from 'react-router-dom'
import { X } from 'lucide-react'
import { getHistory, getRatings, getWatchlist } from '../api/account.js'
import { removeWatchlist, unmarkWatched, unrateMovie } from '../api/user.js'
import { errorMessage } from '../api/client.js'
import MovieCard from '../components/MovieCard.jsx'
import Pagination from '../components/Pagination.jsx'
import Spinner from '../components/Spinner.jsx'
import Tabs from '../components/Tabs.jsx'
import useLoad from '../hooks/useLoad.js'

const TABS = [['watchlist', 'Watchlist'], ['rated', 'Rated'], ['watched', 'Watched']]
const FETCH = { watchlist: getWatchlist, rated: getRatings, watched: getHistory }
const REMOVE = { watchlist: removeWatchlist, rated: unrateMovie, watched: unmarkWatched }
const REMOVE_LABEL = { watchlist: 'Remove from watchlist', rated: 'Clear rating', watched: 'Remove from watched' }
const EMPTY = {
  watchlist: 'Your watchlist is empty. Add movies from their detail pages.',
  rated: 'You have not rated any movies yet. Ratings make your recommendations better.',
  watched: 'Nothing marked as watched yet.',
}

export default function Watchlist() {
  const [tab, setTab] = useState('watchlist')
  const [page, setPage] = useState(1)
  const [note, setNote] = useState('')
  const s = useLoad(() => FETCH[tab](page), [tab, page])

  const remove = async (movieId) => {
    setNote('')
    try {
      await REMOVE[tab](movieId)
      if (s.data.items.length === 1 && page > 1) setPage(page - 1)
      else s.reload()
    } catch (e) {
      setNote(errorMessage(e))
    }
  }

  return (
    <div className="container-page py-10">
      <h1 className="text-3xl">Your movies</h1>
      <div className="mt-5">
        <Tabs tabs={TABS} value={tab} onChange={(t) => { setTab(t); setPage(1) }} />
      </div>

      {note && <p className="card mt-4 p-3 text-sm text-red-300">{note}</p>}
      {s.error && <p className="card mt-6 p-4 text-sm text-red-300">{s.error}</p>}
      {s.loading && !s.data && <Spinner />}

      {s.data && (
        s.data.items.length === 0 ? (
          <div className="card mt-6 p-8 text-center text-mute">
            <p>{EMPTY[tab]}</p>
            <Link to="/discover" className="btn-primary mt-4">Discover movies</Link>
          </div>
        ) : (
          <>
            <p className="mb-3 mt-6 text-sm text-mute">{s.data.total} {s.data.total === 1 ? 'movie' : 'movies'}</p>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
              {s.data.items.map((i) => (
                <div key={i.movie.id} className="relative">
                  <MovieCard movie={i.movie}
                    reason={tab === 'rated' && i.rating != null ? `Your rating: ${i.rating}/5` : undefined} />
                  <button onClick={() => remove(i.movie.id)} title={REMOVE_LABEL[tab]} aria-label={REMOVE_LABEL[tab]}
                    className="absolute right-2 top-2 rounded-full bg-canvas/80 p-1 text-mute backdrop-blur-sm hover:text-gold">
                    <X size={14} />
                  </button>
                </div>
              ))}
            </div>
            <Pagination page={page} pages={s.data.pages} onChange={setPage} />
          </>
        )
      )}
    </div>
  )
}