import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowDown, ArrowUp, FileText } from 'lucide-react'
import api from '../lib/api'
import StatusPill from '../components/StatusPill'

function fmtDate(s) {
  if (!s) return '—'
  return new Date(s).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export default function History() {
  const [items, setItems] = useState(null)
  const [dir, setDir] = useState('desc')

  useEffect(() => {
    ;(async () => {
      try {
        const { data } = await api.get('/analyses')
        setItems(Array.isArray(data) ? data : data?.items || [])
      } catch {
        setItems([])
      }
    })()
  }, [])

  const sorted = useMemo(() => {
    if (!items) return null
    const arr = [...items]
    arr.sort((a, b) => {
      const ta = new Date(a.created_at).getTime() || 0
      const tb = new Date(b.created_at).getTime() || 0
      return dir === 'desc' ? tb - ta : ta - tb
    })
    return arr
  }, [items, dir])

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between mb-6 gap-4">
        <div>
          <div className="font-mono text-xs uppercase tracking-[0.18em] text-ink-500 mb-1">All analyses</div>
          <h1 className="font-serif text-[36px] sm:text-[40px] tracking-[-0.02em] text-ink-900">History</h1>
        </div>
        <button
          type="button"
          onClick={() => setDir((d) => (d === 'desc' ? 'asc' : 'desc'))}
          className="btn-secondary"
          aria-label="Toggle sort direction"
        >
          {dir === 'desc' ? <ArrowDown size={14} /> : <ArrowUp size={14} />}
          Date {dir === 'desc' ? 'newest' : 'oldest'}
        </button>
      </div>

      {sorted === null ? (
        <div className="rounded-[8px] border border-rule-200 bg-paper-50 divide-y divide-rule-200">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="p-4 flex items-center gap-3">
              <div className="ed-skeleton h-9 w-9 rounded-[4px]" />
              <div className="flex-1">
                <div className="ed-skeleton h-3 w-48 mb-2" />
                <div className="ed-skeleton h-3 w-24" />
              </div>
              <div className="ed-skeleton h-6 w-20 rounded-[4px]" />
            </div>
          ))}
        </div>
      ) : sorted.length === 0 ? (
        <div className="rounded-[8px] border border-rule-300 bg-cream-50/60 p-10 text-center text-sm text-ink-500 italic font-serif">
          No analyses yet. Create a project and upload a dataset.
        </div>
      ) : (
        <div className="rounded-[8px] border border-rule-200 bg-paper-50 overflow-hidden">
          <div className="hidden md:grid md:grid-cols-[1.6fr_1fr_120px_180px] px-4 py-2.5 text-[11px] uppercase tracking-[0.14em] text-ink-500 bg-cream-50 border-b border-rule-200">
            <span>File</span>
            <span>Status</span>
            <span>Reviews</span>
            <span>Created</span>
          </div>
          <ul className="divide-y divide-rule-200">
            {sorted.map((a) => (
              <li
                key={a.id}
                className="grid grid-cols-1 md:grid-cols-[1.6fr_1fr_120px_180px] items-center gap-y-2 gap-x-4 px-4 py-3"
              >
                <Link to={`/analyses/${a.id}`} className="flex items-center gap-3 min-w-0 hover:opacity-90">
                  <span className="grid place-items-center h-9 w-9 rounded-[4px] shrink-0 bg-cream-100 text-ink-500 shadow-[inset_0_0_0_1px_var(--rule-300)]">
                    <FileText size={15} />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-medium truncate text-ink-900">{a.file_name}</span>
                    <span className="block text-xs text-ink-500">{a.project?.name || `Project #${a.project_id}`}</span>
                  </span>
                </Link>
                <span>
                  <StatusPill status={a.status} />
                </span>
                <span className="text-sm tabular-nums font-mono text-ink-900">{a.total_reviews ?? '—'} reviews</span>
                <span className="text-sm font-mono text-ink-500">{fmtDate(a.created_at)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
