import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { X } from 'lucide-react'
import { getPreferences, getRecent, savePreferences } from '../api/account.js'
import { errorMessage } from '../api/client.js'
import { filterOptions } from '../api/movies.js'
import ActorPicker from '../components/ActorPicker.jsx'
import Avatar from '../components/Avatar.jsx'
import Chip from '../components/Chip.jsx'
import LanguageChips from '../components/LanguageChips.jsx'
import MovieCard from '../components/MovieCard.jsx'
import Spinner from '../components/Spinner.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { fmtDate } from '../utils.js'

const fromApi = (p) => ({ languages: p.languages.map((l) => l.code), genres: p.genres, actors: p.actors })

export default function Profile() {
  const { user } = useAuth()
  const [prefs, setPrefs] = useState(null)
  const [genres, setGenres] = useState([])
  const [recent, setRecent] = useState([])
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState({ ok: true, text: '' })

  useEffect(() => {
    getPreferences().then((p) => setPrefs(fromApi(p))).catch((e) => setMsg({ ok: false, text: errorMessage(e) }))
    filterOptions().then((o) => setGenres(o.genres)).catch(() => {})
    getRecent(12).then(setRecent).catch(() => {})
  }, [])

  const toggleGenre = (g) =>
    setPrefs((p) => ({ ...p, genres: p.genres.includes(g) ? p.genres.filter((x) => x !== g) : [...p.genres, g] }))
  const addActor = (a) =>
    setPrefs((p) => (p.actors.some((x) => x.id === a.id) ? p : { ...p, actors: [...p.actors, a] }))
  const removeActor = (id) => setPrefs((p) => ({ ...p, actors: p.actors.filter((a) => a.id !== id) }))

  const save = async () => {
    setBusy(true)
    setMsg({ ok: true, text: '' })
    try {
      const saved = await savePreferences({
        languages: prefs.languages, genres: prefs.genres, actor_ids: prefs.actors.map((a) => a.id),
      })
      setPrefs(fromApi(saved))
      setMsg({ ok: true, text: 'Saved. Your recommendations now use these favourites.' })
    } catch (e) {
      setMsg({ ok: false, text: errorMessage(e) })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="container-page py-10">
      <h1 className="text-3xl">Profile</h1>

      <div className="card mt-6 flex flex-wrap items-center gap-5 p-5">
        <span className="flex h-14 w-14 items-center justify-center rounded-full bg-gold font-serif text-2xl text-canvas">
          {user.username[0].toUpperCase()}
        </span>
        <div>
          <p className="text-lg text-ink">{user.username}</p>
          <p className="text-sm text-mute">{user.email}</p>
          <p className="text-xs text-mute">
            {user.role === 'admin' ? 'Administrator' : 'Member'} since {fmtDate(user.created_at).split(',')[0]}
          </p>
        </div>
        <Link to="/taste" className="btn-ghost ml-auto">See my taste profile</Link>
      </div>

      <section className="card mt-6 space-y-6 p-5">
        <div>
          <h2 className="text-xl">Your favourites</h2>
          <p className="mt-1 text-sm text-mute">
            These shape your recommendations from day one, before you have rated anything.
          </p>
        </div>

        {!prefs ? <Spinner /> : (
          <>
            <div>
              <p className="mb-2 text-xs uppercase tracking-wide text-mute">Languages</p>
              <LanguageChips value={prefs.languages} onChange={(languages) => setPrefs({ ...prefs, languages })} />
            </div>
            <div>
              <p className="mb-2 text-xs uppercase tracking-wide text-mute">Genres</p>
              <div className="flex flex-wrap gap-2">
                {genres.map((g) => (
                  <Chip key={g} active={prefs.genres.includes(g)} onClick={() => toggleGenre(g)}>{g}</Chip>
                ))}
              </div>
            </div>
            <div>
              <p className="mb-2 text-xs uppercase tracking-wide text-mute">Favourite actors and actresses</p>
              <div className="max-w-md"><ActorPicker onPick={addActor} /></div>
              {prefs.actors.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {prefs.actors.map((a) => (
                    <span key={a.id} className="flex items-center gap-2 rounded-full border border-line py-1 pl-1 pr-3 text-sm">
                      <Avatar url={a.profile_url} name={a.name} size="h-6 w-6" />
                      {a.name}
                      <button onClick={() => removeActor(a.id)} aria-label={`Remove ${a.name}`}
                        className="text-mute hover:text-gold"><X size={14} /></button>
                    </span>
                  ))}
                </div>
              )}
            </div>
            <div className="flex items-center gap-4">
              <button className="btn-primary" disabled={busy} onClick={save}>
                {busy ? 'Saving...' : 'Save favourites'}
              </button>
              {msg.text && <p className={`text-sm ${msg.ok ? 'text-gold-soft' : 'text-red-300'}`}>{msg.text}</p>}
            </div>
          </>
        )}
      </section>

      <section className="mt-10">
        <h2 className="text-2xl">Recently viewed</h2>
        {recent.length === 0 ? (
          <p className="mt-3 text-sm text-mute">Movies you open while logged in appear here.</p>
        ) : (
          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
            {recent.map((i) => <MovieCard key={i.movie.id} movie={i.movie} />)}
          </div>
        )}
      </section>
    </div>
  )
}