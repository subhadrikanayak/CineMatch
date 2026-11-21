import Chip from './Chip.jsx'

export const LANGUAGES = [
  { code: 'hi', name: 'Hindi' },
  { code: 'te', name: 'Telugu' },
  { code: 'ta', name: 'Tamil' },
  { code: 'ml', name: 'Malayalam' },
  { code: 'kn', name: 'Kannada' },
]

export default function LanguageChips({ value, onChange }) {
  const toggle = (code) =>
    onChange(value.includes(code) ? value.filter((c) => c !== code) : [...value, code])
  return (
    <div className="flex flex-wrap gap-2">
      {LANGUAGES.map((l) => (
        <Chip key={l.code} active={value.includes(l.code)} onClick={() => toggle(l.code)}>
          {l.name}
        </Chip>
      ))}
    </div>
  )
}