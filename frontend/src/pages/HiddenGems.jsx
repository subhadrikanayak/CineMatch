import { useEffect, useState } from 'react'
import { errorMessage } from '../api/client.js'
import { hiddenGems } from '../api/movies.js'
import LanguageChips from '../components/LanguageChips.jsx'
import MovieCard from '../components/MovieCard.jsx'
import Spinner from '../components/Spinner.jsx'

export default function HiddenGems() {
  const [langs, setLangs] = useState([])
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    hiddenGems({ language: langs.length ? langs : undefined, limit: 24 })
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && (setError(errorMessage(e)), setData(null)))
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [langs])

  const th = data?.thresholds

  return (
    <div className="container-page py-10">
      <h1 className="text-3xl">Hidden gems</h1>
      <p className="mt-2 max-w-2xl text-mute">
        Well-rated films that fewer people have found. A movie needs a credible number of votes,
        a high weighted rating and modest popularity, so a handful of votes never counts as excellent.
      </p>

      <div className="mt-6">
        <LanguageChips value={langs} onChange={setLangs} />
      </div>

      {error && <p className="card mt-6 p-4 text-sm text-red-300">{error}</p>}
      {loading && <Spinner label="Digging for gems" />}

      {data && !loading && (
        <>
          {data.items.length === 0 ? (
            <p className="card mt-6 p-6 text-center text-mute">
              No hidden gems match these filters. Try another language, or load more movies.
            </p>
          ) : (
            <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
              {data.items.map((g) => (
                <MovieCard key={g.movie.id} movie={g.movie} reason={g.reasons[1] || g.reasons[0]} />
              ))}
            </div>
          )}
          {th && Object.keys(th).length > 0 && (
            <p className="mt-6 text-xs text-mute">
              Thresholds from this catalogue: at least {th.min_votes} votes, at most{' '}
              {Math.round(th.max_votes)} votes, weighted rating of {th.min_weighted_rating} or more.
            </p>
          )}
        </>
      )}
    </div>
  )
}