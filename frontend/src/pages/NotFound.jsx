import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="container-page py-24 text-center">
      <h1 className="text-3xl">Page not found</h1>
      <p className="mt-3 text-mute">That address doesn't exist.</p>
      <Link to="/" className="btn-primary mt-6">Go home</Link>
    </div>
  )
}
