import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { errorMessage } from '../api/client.js'
import { useAuth } from '../context/AuthContext.jsx'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', username: '', password: '', confirm: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    if (form.password.length < 8) return setError('Password must be at least 8 characters')
    if (form.password !== form.confirm) return setError('Passwords do not match')
    setBusy(true)
    try {
      await register(form.email.trim(), form.username.trim(), form.password)
      navigate('/', { replace: true })
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="container-page flex justify-center py-16">
      <form onSubmit={submit} className="card w-full max-w-sm space-y-4 p-6">
        <h1 className="text-2xl">Create your account</h1>
        <div>
          <label className="mb-1 block text-xs text-mute" htmlFor="email">Email</label>
          <input id="email" type="email" className="input" value={form.email}
            autoComplete="email" onChange={set('email')} required />
        </div>
        <div>
          <label className="mb-1 block text-xs text-mute" htmlFor="username">Username</label>
          <input id="username" className="input" value={form.username} minLength={3}
            autoComplete="username" onChange={set('username')} required />
          <p className="mt-1 text-xs text-mute">Letters, numbers, dot, dash and underscore.</p>
        </div>
        <div>
          <label className="mb-1 block text-xs text-mute" htmlFor="pw">Password</label>
          <input id="pw" type="password" className="input" value={form.password}
            autoComplete="new-password" onChange={set('password')} required />
        </div>
        <div>
          <label className="mb-1 block text-xs text-mute" htmlFor="pw2">Confirm password</label>
          <input id="pw2" type="password" className="input" value={form.confirm}
            autoComplete="new-password" onChange={set('confirm')} required />
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
        <button className="btn-primary w-full" disabled={busy}>
          {busy ? 'Creating account...' : 'Sign up'}
        </button>
        <p className="text-center text-sm text-mute">
          Already registered? <Link to="/login" className="text-gold hover:underline">Log in</Link>
        </p>
      </form>
    </div>
  )
}