import { Link } from 'react-router-dom'

export default function ComingSoon({ title }) {
  return (
    <div className="container-page py-24 text-center">
      <h1 className="text-3xl">{title}</h1>
      <p className="mx-auto mt-3 max-w-md text-mute">
        This page is built in Phase 10. The backend for it already works.
      </p>
      <Link to="/" className="btn-ghost mt-6">Back to home</Link>
    </div>
  )
}