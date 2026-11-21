export default function Tabs({ tabs, value, onChange }) {
  return (
    <div className="flex flex-wrap gap-2 border-b border-line pb-3">
      {tabs.map(([id, label]) => (
        <button key={id} onClick={() => onChange(id)}
          className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
            value === id ? 'bg-gold/15 text-gold' : 'text-mute hover:text-ink'}`}>
          {label}
        </button>
      ))}
    </div>
  )
}