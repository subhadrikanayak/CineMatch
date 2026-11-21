import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import * as adminApi from '../api/admin.js'
import { errorMessage } from '../api/client.js'
import { LANGUAGES } from '../components/LanguageChips.jsx'
import Chip from '../components/Chip.jsx'
import Pagination from '../components/Pagination.jsx'
import Spinner from '../components/Spinner.jsx'
import Tabs from '../components/Tabs.jsx'
import useLoad from '../hooks/useLoad.js'
import { chart, fmtDate } from '../utils.js'

const TABS = [
  ['overview', 'Overview'], ['catalogue', 'Catalogue'], ['trends', 'Trends'], ['users', 'User activity'],
  ['popular', 'Popular movies'], ['recs', 'Recommendations'], ['tools', 'Maintenance'],
]

function Async({ s, children }) {
  if (s.loading && !s.data) return <Spinner />
  if (s.error) return <p className="card p-4 text-sm text-red-300">{s.error}</p>
  return s.data ? children(s.data) : null
}

const Stat = ({ label, value, hint }) => (
  <div className="card p-4">
    <p className="text-xs uppercase tracking-wide text-mute">{label}</p>
    <p className="mt-1 font-serif text-2xl text-ink">{typeof value === 'number' ? value.toLocaleString() : value}</p>
    {hint && <p className="mt-1 text-xs text-mute">{hint}</p>}
  </div>
)

const Facts = ({ title, rows }) => (
  <div className="card p-4">
    <h3 className="text-lg">{title}</h3>
    <dl className="mt-3 space-y-2 text-sm">
      {rows.map(([k, v]) => (
        <div key={k} className="flex justify-between gap-4">
          <dt className="text-mute">{k}</dt>
          <dd className="text-right text-ink">{v}</dd>
        </div>
      ))}
    </dl>
  </div>
)

function Overview() {
  const s = useLoad(adminApi.stats, [])
  return (
    <Async s={s}>
      {(d) => (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label="Users" value={d.users} hint={`${d.active_users_7d} active in 7 days`} />
            <Stat label="Movies" value={d.movies} />
            <Stat label="Ratings" value={d.ratings} />
            <Stat label="Watchlist items" value={d.watchlist_items} />
            <Stat label="Feedback" value={d.feedback} />
            <Stat label="Recommendations served" value={d.recommendations_served} />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <Facts title="Catalogue health" rows={[
              ...Object.entries(d.catalogue.by_rating_source).map(([k, v]) => [`Rating source: ${k}`, v]),
              ['With IMDb rating', d.catalogue.with_imdb_rating],
              ['Missing overview', d.catalogue.missing_overview],
              ['Missing poster', d.catalogue.missing_poster],
              ['With streaming data', d.catalogue.with_streaming_data],
            ]} />
            <Facts title="Recommendation engine" rows={[
              ['Loaded', d.engine.loaded ? 'yes' : 'no'],
              ['Movies in model', d.engine.movies_in_model],
              ['Collaborative filtering', d.engine.collaborative_ready ? 'active' : 'off'],
              ['Ratings in database', `${d.engine.ratings_in_db} of ${d.engine.ratings_needed} needed`],
              ['Users who rated', `${d.engine.users_who_rated} of ${d.engine.users_needed} needed`],
              ['Semantic search', d.engine.semantic_engine || '-'],
            ]} />
          </div>
        </div>
      )}
    </Async>
  )
}

function Catalogue() {
  const [text, setText] = useState('')
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const s = useLoad(() => adminApi.catalogue({ q: q || undefined, page, page_size: 25 }), [q, page])
  return (
    <div>
      <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); setQ(text.trim()); setPage(1) }}>
        <input className="input max-w-sm" value={text} onChange={(e) => setText(e.target.value)} placeholder="Search the catalogue" />
        <button className="btn-primary">Search</button>
      </form>
      <div className="mt-4">
        <Async s={s}>
          {(d) => (
            <>
              <p className="mb-2 text-sm text-mute">{d.total} movies</p>
              <div className="card overflow-x-auto">
                <table className="w-full min-w-[640px] text-sm">
                  <thead className="text-left text-xs uppercase tracking-wide text-mute">
                    <tr><th className="p-3">Title</th><th>Language</th><th>Year</th><th>Rating</th><th>Votes</th></tr>
                  </thead>
                  <tbody>
                    {d.items.map((m) => (
                      <tr key={m.id} className="border-t border-line">
                        <td className="p-3"><Link to={`/movies/${m.id}`} className="hover:text-gold">{m.title}</Link></td>
                        <td>{m.language}</td>
                        <td>{m.release_year || '-'}</td>
                        <td>{m.rating != null ? `${m.rating.toFixed(1)} ${m.rating_source.toUpperCase()}` : '-'}</td>
                        <td>{m.votes?.toLocaleString() ?? '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Pagination page={page} pages={d.pages} onChange={setPage} />
            </>
          )}
        </Async>
      </div>
    </div>
  )
}

function TrendChart({ title, rows, height = 280, vertical = false }) {
  return (
    <div className="card p-4">
      <h3 className="text-lg">{title}</h3>
      <div className="mt-3" style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} layout={vertical ? 'vertical' : 'horizontal'} margin={{ left: 8, right: 16 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.06)" />
            {vertical ? (
              <>
                <XAxis type="number" tick={chart.tick} allowDecimals={false} />
                <YAxis type="category" dataKey="name" width={80} tick={chart.tick} />
              </>
            ) : (
              <>
                <XAxis dataKey="name" tick={chart.tick} />
                <YAxis tick={chart.tick} allowDecimals={false} />
              </>
            )}
            <Tooltip {...chart.tooltip} />
            <Legend />
            <Bar dataKey="catalogue" name="Movies in catalogue" fill={chart.violet} radius={3} />
            <Bar dataKey="engagement" name="User engagement" fill={chart.accent} radius={3} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function Trends() {
  const l = useLoad(adminApi.languageTrends, [])
  const g = useLoad(adminApi.genreTrends, [])
  const none = (d) => d.every((r) => r.engagement === 0)
  return (
    <div className="space-y-4">
      <Async s={l}>
        {(d) => (
          <>
            <TrendChart title="Languages" rows={d} />
            {none(d) && <p className="text-xs text-mute">No user activity yet, so only catalogue sizes are meaningful.</p>}
          </>
        )}
      </Async>
      <Async s={g}>{(d) => <TrendChart title="Genres" rows={d} vertical height={Math.max(280, d.length * 36)} />}</Async>
      <p className="text-xs text-mute">Engagement = movie page views + ratings + watchlist additions, from logged-in users.</p>
    </div>
  )
}

function Users() {
  const [page, setPage] = useState(1)
  const s = useLoad(() => adminApi.usersActivity(page), [page])
  return (
    <Async s={s}>
      {(d) => (
        <>
          <div className="card overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-mute">
                <tr><th className="p-3">User</th><th>Views</th><th>Ratings</th><th>Watchlist</th><th>Recs received</th><th>Last active</th></tr>
              </thead>
              <tbody>
                {d.items.map((u) => (
                  <tr key={u.id} className="border-t border-line">
                    <td className="p-3 text-ink">{u.username}</td>
                    <td>{u.views}</td><td>{u.ratings}</td><td>{u.watchlist}</td>
                    <td>{u.recommendations_received}</td><td>{fmtDate(u.last_active)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} pages={Math.ceil(d.total / d.page_size)} onChange={setPage} />
        </>
      )}
    </Async>
  )
}

function Popular() {
  const [by, setBy] = useState('views')
  const s = useLoad(() => adminApi.popularMovies(by), [by])
  return (
    <div>
      <div className="flex gap-2">
        {['views', 'ratings', 'watchlist'].map((k) => (
          <Chip key={k} active={by === k} onClick={() => setBy(k)}>{k}</Chip>
        ))}
      </div>
      <div className="mt-4">
        <Async s={s}>
          {(d) => d.length === 0 ? (
            <p className="card p-6 text-center text-mute">No activity recorded yet.</p>
          ) : (
            <ol className="card divide-y divide-line">
              {d.map((r, i) => (
                <li key={r.movie.id} className="flex items-center justify-between p-3 text-sm">
                  <span><span className="mr-3 text-mute">{i + 1}</span>
                    <Link to={`/movies/${r.movie.id}`} className="text-ink hover:text-gold">{r.movie.title}</Link></span>
                  <span className="text-mute">{r.count} {by}</span>
                </li>
              ))}
            </ol>
          )}
        </Async>
      </div>
    </div>
  )
}

function Recs() {
  const s = useLoad(adminApi.recAnalytics, [])
  return (
    <Async s={s}>
      {(d) => (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label="Served" value={d.total_served} />
            <Stat label="Users served" value={d.users_served} />
            <Stat label="Likes" value={d.feedback.likes} />
            <Stat label="Like rate" value={d.feedback.like_rate_percent != null ? `${d.feedback.like_rate_percent}%` : '-'}
              hint={`${d.feedback.dislikes} dislikes, ${d.feedback.comments} comments`} />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="card p-4">
              <h3 className="text-lg">By source</h3>
              {d.by_source.length === 0 ? <p className="mt-3 text-sm text-mute">Nothing served to logged-in users yet.</p> : (
                <ul className="mt-3 space-y-2 text-sm">
                  {d.by_source.map((r) => (
                    <li key={r.source} className="flex justify-between">
                      <span className="text-ink">{r.source}</span>
                      <span className="text-mute">{r.served} served, avg score {r.avg_match_percent}%</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div className="card p-4">
              <h3 className="text-lg">Most recommended</h3>
              {d.most_recommended.length === 0 ? <p className="mt-3 text-sm text-mute">No data yet.</p> : (
                <ol className="mt-3 space-y-2 text-sm">
                  {d.most_recommended.map((r) => (
                    <li key={r.movie.id} className="flex justify-between">
                      <Link to={`/movies/${r.movie.id}`} className="text-ink hover:text-gold">{r.movie.title}</Link>
                      <span className="text-mute">{r.times}x</span>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </div>
          <div className="card p-4">
            <h3 className="text-lg">Last 14 days</h3>
            {d.last_14_days.length === 0 ? <p className="mt-3 text-sm text-mute">No recommendations served recently.</p> : (
              <div className="mt-3 h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={d.last_14_days}>
                    <CartesianGrid stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="date" tick={chart.tick} />
                    <YAxis tick={chart.tick} allowDecimals={false} />
                    <Tooltip {...chart.tooltip} />
                    <Bar dataKey="served" name="Served" fill={chart.accent} radius={3} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
          <p className="text-xs text-mute">Only recommendations shown to logged-in users are logged.</p>
        </div>
      )}
    </Async>
  )
}

function Tools() {
  const [retrain, setRetrain] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [pages, setPages] = useState(2)
  const [langs, setLangs] = useState([])
  const [status, setStatus] = useState(null)

  const refresh = () => adminApi.ingestStatus().then(setStatus).catch((e) => setErr(errorMessage(e)))
  useEffect(() => { refresh() }, [])
  useEffect(() => {
    if (!status?.running) return
    const t = setInterval(refresh, 4000)
    return () => clearInterval(t)
  }, [status?.running])

  const doRetrain = async () => {
    setBusy(true); setErr(''); setRetrain(null)
    try { setRetrain(await adminApi.retrain()) } catch (e) { setErr(errorMessage(e)) } finally { setBusy(false) }
  }
  const doIngest = async () => {
    setErr('')
    try {
      await adminApi.startIngest({ pages, languages: langs.length ? langs : LANGUAGES.map((l) => l.code) })
      refresh()
    } catch (e) { setErr(errorMessage(e)) }
  }
  const toggle = (c) => setLangs((p) => (p.includes(c) ? p.filter((x) => x !== c) : [...p, c]))

  return (
    <div className="space-y-4">
      {err && <p className="card p-4 text-sm text-red-300">{err}</p>}

      <div className="card p-4">
        <h3 className="text-lg">Retrain models</h3>
        <p className="mt-1 text-sm text-mute">
          Refits TF-IDF and the collaborative model on the current database, then reloads the engine.
          Run it after loading movies or after new ratings arrive.
        </p>
        <button className="btn-primary mt-3" disabled={busy} onClick={doRetrain}>
          {busy ? 'Training...' : 'Retrain now'}
        </button>
        {retrain && (
          <p className="mt-3 text-sm text-mute">
            Done: {retrain.movies} movies, {retrain.tfidf_features} features, {retrain.ratings_used} ratings used.
            Collaborative filtering is {retrain.collaborative_ready ? 'active' : 'off (not enough real ratings yet)'}.
          </p>
        )}
      </div>

      <div className="card p-4">
        <h3 className="text-lg">Load more movies from TMDB</h3>
        <p className="mt-1 text-sm text-mute">Needs your VPN on. Takes 10 to 20 minutes. Retrain afterwards.</p>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <select className="input w-auto" value={pages} onChange={(e) => setPages(Number(e.target.value))}>
            {[1, 2, 3, 5, 10].map((n) => <option key={n} value={n}>{n} pages per language</option>)}
          </select>
          {LANGUAGES.map((l) => (
            <Chip key={l.code} active={langs.includes(l.code)} onClick={() => toggle(l.code)}>{l.name}</Chip>
          ))}
          <span className="text-xs text-mute">{langs.length ? '' : 'none selected = all five'}</span>
        </div>
        <button className="btn-primary mt-3" disabled={status?.running} onClick={doIngest}>
          {status?.running ? 'Running...' : 'Start ingestion'}
        </button>
        {status && (status.running || status.last_log_lines.length > 0) && (
          <pre className="mt-3 max-h-60 overflow-auto rounded-lg bg-black/30 p-3 text-xs text-mute">
            {status.last_log_lines.join('\n')}
          </pre>
        )}
        {status && !status.running && status.exit_code != null && (
          <p className="mt-2 text-sm text-mute">
            Finished {status.exit_code === 0 ? 'successfully' : `with exit code ${status.exit_code}`}.
          </p>
        )}
      </div>
    </div>
  )
}

const VIEWS = { overview: Overview, catalogue: Catalogue, trends: Trends, users: Users, popular: Popular, recs: Recs, tools: Tools }

export default function Admin() {
  const [tab, setTab] = useState('overview')
  const View = VIEWS[tab]
  return (
    <div className="container-page py-10">
      <h1 className="text-3xl">Admin dashboard</h1>
      <div className="mt-5"><Tabs tabs={TABS} value={tab} onChange={setTab} /></div>
      <div className="mt-6"><View /></div>
    </div>
  )
}