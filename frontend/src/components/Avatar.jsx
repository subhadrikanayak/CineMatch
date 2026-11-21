import { Link } from 'react-router-dom'
import { User } from 'lucide-react'

export default function Avatar({ url, name, size = 'h-12 w-12' }) {
  return (
    <div className={`${size} shrink-0 overflow-hidden rounded-full border border-line bg-black/20`}>
      {url ? (
        <img src={url} alt={name} loading="lazy" className="h-full w-full object-cover" />
      ) : (
        <div className="flex h-full w-full items-center justify-center text-mute/40">
          <User size={18} />
        </div>
      )}
    </div>
  )
}

const ROLE = { male: 'Actor', female: 'Actress' }

export function PersonTile({ person }) {
  return (
    <Link to={`/people/${person.id}`}
      className="card flex items-center gap-3 p-3 transition-colors hover:border-gold-dim">
      <Avatar url={person.profile_url} name={person.name} size="h-14 w-14" />
      <div className="min-w-0">
        <p className="line-clamp-1 text-sm text-ink">{person.name}</p>
        <p className="text-xs text-mute">{ROLE[person.gender] || 'Cast'}</p>
      </div>
    </Link>
  )
}