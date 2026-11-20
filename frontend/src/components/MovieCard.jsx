import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Film, Star } from 'lucide-react'

export default function MovieCard({ movie, match, reason }) {
  const [broken, setBroken] = useState(false)

  return (
    <Link
      to={`/movies/${movie.id}`}
      className="group block overflow-hidden rounded-xl border border-line bg-surface shadow-soft backdrop-blur-md transition-all duration-300 hover:border-gold-dim hover:bg-white/10"
    >
      <div className="relative aspect-[2/3] bg-black/20">
        {movie.poster_url && !broken ? (
          <img
            src={movie.poster_url}
            alt={`${movie.title} poster`}
            loading="lazy"
            onError={() => setBroken(true)}
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-mute/40">
            <Film size={40} />
          </div>
        )}
        {match != null && (
          <span className="absolute left-2 top-2 rounded-md bg-canvas/70 px-2 py-0.5 text-xs font-medium text-gold backdrop-blur-sm">
            {match}% match
          </span>
        )}
      </div>

      <div className="space-y-1 p-3">
        <h3 className="line-clamp-1 font-sans text-sm font-medium text-ink">{movie.title}</h3>
        <p className="text-xs text-mute">
          {[movie.release_year, movie.language].filter(Boolean).join(' · ')}
        </p>
        <div className="flex items-center gap-1 text-xs">
          <Star size={12} className="text-gold" fill="currentColor" />
          {movie.rating != null ? (
            <span className="text-ink">
              {movie.rating.toFixed(1)}{' '}
              <span className="text-mute">{movie.rating_source?.toUpperCase()}</span>
            </span>
          ) : (
            <span className="text-mute">No rating yet</span>
          )}
        </div>
        {movie.genres.length > 0 && (
          <p className="line-clamp-1 text-xs text-mute">{movie.genres.slice(0, 3).join(', ')}</p>
        )}
        {reason && <p className="line-clamp-2 border-t border-line pt-2 text-xs text-mute">{reason}</p>}
      </div>
    </Link>
  )
}