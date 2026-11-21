export default function Chip({ active, children, ...props }) {
  return (
    <button
      type="button"
      {...props}
      className={`rounded-full border px-3 py-1 text-xs transition-colors ${
        active
          ? 'border-gold bg-gold/15 text-gold'
          : 'border-line text-mute hover:border-gold-dim hover:text-ink'
      }`}
    >
      {children}
    </button>
  )
}