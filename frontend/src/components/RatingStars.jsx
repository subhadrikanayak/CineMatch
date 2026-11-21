import { Star } from 'lucide-react'

// Click the left half of a star for a half rating (0.5 steps, as the API expects).
export default function RatingStars({ value, onChange, disabled }) {
  const v = value || 0
  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map((n) => {
        const width = v >= n ? '100%' : v >= n - 0.5 ? '50%' : '0%'
        return (
          <span key={n} className="relative inline-block h-6 w-6">
            <Star size={24} className="text-mute/40" />
            <span className="absolute inset-0 overflow-hidden" style={{ width }}>
              <Star size={24} className="text-gold" fill="currentColor" />
            </span>
            <button type="button" disabled={disabled} aria-label={`Rate ${n - 0.5} out of 5`}
              onClick={() => onChange(n - 0.5)} className="absolute inset-y-0 left-0 w-1/2" />
            <button type="button" disabled={disabled} aria-label={`Rate ${n} out of 5`}
              onClick={() => onChange(n)} className="absolute inset-y-0 right-0 w-1/2" />
          </span>
        )
      })}
    </div>
  )
}