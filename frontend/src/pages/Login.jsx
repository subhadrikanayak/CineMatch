import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { errorMessage } from '../api/client.js'
import { useAuth } from '../context/AuthContext.jsx'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await login(identifier.trim(), password)
      navigate(location.state?.from || '/', { replace: true })
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="container-page flex justify-center py-16">
      <form onSubmit={submit} className="card w-full max-w-sm space-y-4 p-6">
        <h1 className="text-2xl">Welcome back</h1>
        <div>
          <label className="mb-1 block text-xs text-mute" htmlFor="id">Email or username</label>
          <input id="id" className="input" value={identifier} autoComplete="username"
            onChange={(e) => setIdentifier(e.target.value)} required />
        </div>
        <div>
          <label className="mb-1 block text-xs text-mute" htmlFor="pw">Password</label>
          <input id="pw" type="password" className="input" value={password}
            autoComplete="current-password" onChange={(e) => setPassword(e.target.value)} required />
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
        <button className="btn-primary w-full" disabled={busy}>
          {busy ? 'Logging in...' : 'Log in'}
        </button>
        <p className="text-center text-sm text-mute">
          New here? <Link to="/register" className="text-gold hover:underline">Create an account</Link>
        </p>
      </form>
    </div>
  )
}