export default function Pagination({ page, pages, onChange }) {
  if (pages <= 1) return null
  return (
    <div className="mt-8 flex items-center justify-center gap-3">
      <button className="btn-ghost disabled:opacity-40" disabled={page <= 1}
        onClick={() => onChange(page - 1)}>Previous</button>
      <span className="text-sm text-mute">Page {page} of {pages}</span>
      <button className="btn-ghost disabled:opacity-40" disabled={page >= pages}
        onClick={() => onChange(page + 1)}>Next</button>
    </div>
  )
}