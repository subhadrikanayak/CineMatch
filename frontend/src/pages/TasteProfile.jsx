import { Link } from 'react-router-dom'
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getTaste } from '../api/account.js'
import Spinner from '../components/Spinner.jsx'
import useLoad from '../hooks/useLoad.js'
import { chart } from '../utils.js'

function Share({ title, rows }) {
  if (!rows.length) return null
  return (
    <div className="card p-4">
      <h3 className="text-lg">{title}</h3>
      <div className="mt-3" style={{ height: Math.max(150, rows.length * 34) }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 24 }}>
            <XAxis type="number" tick={chart.tick} unit="%" domain={[0, 'dataMax']} />
            <YAxis type="category" dataKey="name" width={90} tick={chart.tick} />
            <Tooltip {...chart.tooltip} formatter={(v) => `${v}%`} />
            <Bar dataKey="percent" name="Share" fill={chart.accent} radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

const Stat = ({ label, value }) => (
  <div className="card p-4">
    <p className="text-xs uppercase tracking-wide text-mute">{label}</p>
    <p className="mt-1 font-serif text-2xl text-ink">{value ?? '-'}</p>
  </div>
)

function People({ title, rows }) {
  if (!rows.length) return null
  return (
    <div className="card p-4">
      <h3 className="text-lg">{title}</h3>
      <ul className="mt-3 space-y-2 text-sm">
        {rows.map((p) => (
          <li key={p.id} className="flex justify-between">
            <span className="text-ink">{p.name}</span>
            <span className="text-mute">{p.movies} movies</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function TasteProfile() {
  const s = useLoad(getTaste, [])

  if (s.loading && !s.data) return <Spinner label="Analysing your taste" />
  if (s.error) return <div className="container-page py-16 text-center text-mute">{s.error}</div>
  const t = s.data
  const b = t.based_on

  return (
    <div className="container-page py-10">
      <h1 className="text-3xl">Your taste profile</h1>
      <p className="mt-2 text-sm text-mute">
        Based on {b.ratings} ratings, {b.likes} likes, {b.dislikes} dislikes and {b.watchlist} watchlist items.
      </p>

      {!t.enough_data ? (
        <div className="card mt-6 p-8 text-center text-mute">
          <p>We need at least 3 movies you rated 3.5 or higher, liked, or saved to build a real profile.</p>
          <p className="mt-1 text-sm">You have {b.movies_used_for_taste} so far.</p>
          <Link to="/discover" className="btn-primary mt-4">Find movies to rate</Link>
        </div>
      ) : (
        <>
          <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label="Average runtime" value={t.avg_runtime ? `${t.avg_runtime} min` : null} />
            <Stat label="Typical release year" value={t.avg_release_year} />
            <Stat label="Public rating of your picks" value={t.avg_public_rating} />
            <Stat label="Your average rating" value={t.own_average_rating ? `${t.own_average_rating} / 5` : null} />
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <Share title="Genres" rows={t.genres} />
            <Share title="Languages" rows={t.languages} />
            <Share title="Decades" rows={t.decades} />
            <div className="space-y-4">
              <People title="Actors you return to" rows={t.top_actors} />
              <People title="Directors you return to" rows={t.top_directors} />
            </div>
          </div>

          {t.avoided_genres.length > 0 && (
            <p className="mt-6 text-sm text-mute">
              Genres you tend to rate low or dislike: <span className="text-ink">{t.avoided_genres.join(', ')}</span>
            </p>
          )}
        </>
      )}

      {(t.declared.languages.length > 0 || t.declared.genres.length > 0) && (
        <p className="mt-4 text-sm text-mute">
          Declared favourites: {[...t.declared.languages, ...t.declared.genres].join(', ')}.{' '}
          <Link to="/profile" className="text-gold hover:underline">Edit</Link>
        </p>
      )}
      <p className="mt-6 text-xs text-mute">{t.note}</p>
    </div>
  )
}