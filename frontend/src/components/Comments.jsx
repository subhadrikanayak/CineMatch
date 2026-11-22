import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Trash2 } from 'lucide-react'
import { errorMessage } from '../api/client.js'
import * as userApi from '../api/user.js'
import { useAuth } from '../context/AuthContext.jsx'
import { fmtDate } from '../utils.js'

export default function Comments({ movieId }) {
  const { user } = useAuth()
  const [items, setItems] = useState([])
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const load = () => userApi.listComments(movieId).then(setItems).catch(() => {})

  useEffect(() => {
    setItems([])
    setText('')
    load()
  }, [movieId]) // eslint-disable-line

  const submit = async (e) => {
    e.preventDefault()
    if (!text.trim()) return
    setBusy(true)
    setError('')
    try {
      await userApi.addComment(movieId, text.trim())
      setText('')
      await load()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const remove = async (id) => {
    setError('')
    try {
      await userApi.deleteComment(id)
      await load()
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <section className="mt-12">
      <h2 className="text-2xl">Comments</h2>

      {user ? (
        <form onSubmit={submit} className="mt-4 space-y-2">
          <textarea className="input min-h-[90px]" maxLength={1000} value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Share what you thought about this movie" />
          <div className="flex items-center justify-between">
            <span className="text-xs text-mute">{text.length}/1000 · comments are public</span>
            <button className="btn-primary" disabled={busy || !text.trim()}>
              {busy ? 'Posting...' : 'Post comment'}
            </button>
          </div>
        </form>
      ) : (
        <p className="mt-3 text-sm text-mute">
          <Link to="/login" state={{ from: `/movies/${movieId}` }} className="text-gold hover:underline">Log in</Link>{' '}
          to leave a comment.
        </p>
      )}

      {error && <p className="mt-3 text-sm text-red-300">{error}</p>}

      {items.length === 0 ? (
        <p className="mt-4 text-sm text-mute">No comments yet.</p>
      ) : (
        <ul className="mt-4 space-y-3">
          {items.map((c) => (
            <li key={c.id} className="card p-4">
              <div className="flex items-center justify-between text-xs text-mute">
                <span><span className="text-ink">{c.username}</span> · {fmtDate(c.created_at)}</span>
                {user?.id === c.user_id && (
                  <button onClick={() => remove(c.id)} aria-label="Delete comment" className="hover:text-gold">
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
              <p className="mt-2 whitespace-pre-wrap text-sm text-ink/90">{c.comment}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}