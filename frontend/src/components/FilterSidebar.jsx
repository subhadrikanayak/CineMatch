import { useEffect, useState } from 'react'
import Chip from './Chip.jsx'
import LanguageChips from './LanguageChips.jsx'

const SORTS = [
  ['popularity', 'Popularity'],
  ['rating', 'Rating'],
  ['year', 'Newest'],
  ['title', 'Title A to Z'],
]

const EMPTY = {
  language: [], genre: [], genre_match: 'any',
  min_rating: '', year_min: '', year_max: '', runtime_max: '', sort: 'popularity',
}

const fromParams = (p) => ({
  language: p.getAll('language'),
  genre: p.getAll('genre'),
  genre_match: p.get('genre_match') || 'any',
  min_rating: p.get('min_rating') || '',
  year_min: p.get('year_min') || '',
  year_max: p.get('year_max') || '',
  runtime_max: p.get('runtime_max') || '',
  sort: p.get('sort') || 'popularity',
})

function Label({ children }) {
  return <p className="mb-2 text-xs uppercase tracking-wide text-mute">{children}</p>
}

export default function FilterSidebar({ options, params, onApply }) {
  const [d, setD] = useState(() => fromParams(params))
  useEffect(() => setD(fromParams(params)), [params.toString()]) // eslint-disable-line

  const set = (k) => (e) => setD({ ...d, [k]: e.target.value })
  const toggleGenre = (g) =>
    setD({ ...d, genre: d.genre.includes(g) ? d.genre.filter((x) => x !== g) : [...d.genre, g] })

  return (
    <div className="card space-y-5 p-4">
      <div>
        <Label>Language</Label>
        <LanguageChips value={d.language} onChange={(language) => setD({ ...d, language })} />
      </div>

      <div>
        <Label>Genres</Label>
        <div className="flex flex-wrap gap-2">
          {(options?.genres || []).map((g) => (
            <Chip key={g} active={d.genre.includes(g)} onClick={() => toggleGenre(g)}>{g}</Chip>
          ))}
        </div>
        <select className="input mt-3" value={d.genre_match} onChange={set('genre_match')}>
          <option value="any">Match any selected genre</option>
          <option value="all">Match all selected genres</option>
        </select>
      </div>

      <div>
        <Label>Minimum rating</Label>
        <select className="input" value={d.min_rating} onChange={set('min_rating')}>
          <option value="">Any</option>
          {[5, 6, 7, 8].map((r) => <option key={r} value={r}>{r}+</option>)}
        </select>
        <p className="mt-1 text-xs text-mute">IMDb rating, or TMDB when IMDb is not available.</p>
      </div>

      <div>
        <Label>Release year</Label>
        <div className="flex gap-2">
          <input className="input" type="number" placeholder={options?.year_range?.min || 'From'}
            value={d.year_min} onChange={set('year_min')} />
          <input className="input" type="number" placeholder={options?.year_range?.max || 'To'}
            value={d.year_max} onChange={set('year_max')} />
        </div>
      </div>

      <div>
        <Label>Maximum runtime</Label>
        <select className="input" value={d.runtime_max} onChange={set('runtime_max')}>
          <option value="">Any</option>
          {[90, 120, 150, 180].map((r) => <option key={r} value={r}>{r} minutes</option>)}
        </select>
      </div>

      <div>
        <Label>Sort by</Label>
        <select className="input" value={d.sort} onChange={set('sort')}>
          {SORTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
      </div>

      <div className="flex gap-2">
        <button className="btn-primary flex-1" onClick={() => onApply(d)}>Apply</button>
        <button className="btn-ghost" onClick={() => onApply(EMPTY)}>Reset</button>
      </div>
    </div>
  )
}