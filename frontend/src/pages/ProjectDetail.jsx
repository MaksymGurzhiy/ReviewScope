import { useEffect, useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { ChevronRight, Play, Trash2, FileText } from 'lucide-react'
import api from '../lib/api'
import FileUpload from '../components/FileUpload'
import StatusPill from '../components/StatusPill'

function fmtDate(s) {
  if (!s) return '—'
  return new Date(s).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}
function fmtDuration(ms) {
  if (!ms && ms !== 0) return '—'
  if (ms < 1000) return `${ms} ms`
  const s = ms / 1000
  if (s < 60) return `${s.toFixed(1)} s`
  return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`
}

export default function ProjectDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [project, setProject] = useState(null)
  const [analyses, setAnalyses] = useState(null)
  const [running, setRunning] = useState(null)

  const load = async () => {
    const [{ data: p }, { data: a }] = await Promise.all([
      api.get(`/projects/${id}`),
      api.get(`/analyses`, { params: { project_id: id } }),
    ])
    setProject(p)
    setAnalyses(Array.isArray(a) ? a : a?.items || [])
  }

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- refresh when project id changes
  }, [id])

  const upload = async (file) => {
    const fd = new FormData()
    fd.append('project_id', id)
    fd.append('file', file)
    const { data } = await api.post(`/analyses/upload`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    if (data?.id) {
      api.post(`/analyses/${data.id}/run`, {}).catch(() => {})
      navigate(`/analyses/${data.id}`)
    } else {
      await load()
    }
  }

  const run = async (aid) => {
    setRunning(aid)
    try {
      await api.post(`/analyses/${aid}/run`, {})
      navigate(`/analyses/${aid}`)
    } finally {
      setRunning(null)
    }
  }
  const remove = async (aid) => {
    if (!confirm('Delete this analysis?')) return
    await api.delete(`/analyses/${aid}`)
    await load()
  }

  return (
    <div>
      <nav aria-label="Breadcrumb" className="text-sm flex items-center gap-1.5 mb-5 text-ink-500 font-sans">
        <Link to="/projects" className="hover:text-ink-900 transition-colors uppercase tracking-[0.12em] text-xs">
          Projects
        </Link>
        <ChevronRight size={14} className="shrink-0" />
        <span className="text-ink-900 truncate">{project?.name || '…'}</span>
      </nav>

      <header className="mb-6">
        <h1 className="font-serif text-[36px] sm:text-[42px] tracking-[-0.02em] text-ink-900">
          {project?.name || <span className="ed-skeleton inline-block h-9 w-48 rounded-[4px]" />}
        </h1>
        {project?.description && (
          <p className="text-sm mt-1.5 max-w-2xl text-ink-600">{project.description}</p>
        )}
      </header>

      <section className="rounded-[8px] border border-rule-300 bg-paper-50 p-6 mb-8 shadow-[inset_0_1px_0_0_var(--rule-200)]">
        <div className="flex items-start justify-between mb-4 gap-4">
          <div>
            <h2 className="font-serif text-[22px] text-ink-900">Upload reviews</h2>
            <p className="text-xs mt-1 text-ink-500">Drop a CSV, XLSX or JSON file to start a new analysis.</p>
          </div>
        </div>
        <FileUpload onUpload={upload} />
      </section>

      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-serif text-[22px] text-ink-900">Analyses</h2>
          <span className="text-xs tabular-nums font-mono text-ink-500">
            {analyses ? analyses.length : '…'} total
          </span>
        </div>

        {analyses === null ? (
          <div className="rounded-[8px] border border-rule-200 bg-paper-50 divide-y divide-rule-200">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="p-4 flex items-center gap-4">
                <div className="ed-skeleton h-9 w-9 rounded-[4px]" />
                <div className="flex-1">
                  <div className="ed-skeleton h-3 w-40 mb-2" />
                  <div className="ed-skeleton h-3 w-24" />
                </div>
                <div className="ed-skeleton h-6 w-20 rounded-[4px]" />
              </div>
            ))}
          </div>
        ) : analyses.length === 0 ? (
          <div className="rounded-[8px] border border-rule-300 bg-cream-50/60 p-10 text-center">
            <p className="text-sm text-ink-500 italic font-serif">
              No analyses yet. Upload a dataset above to get started.
            </p>
          </div>
        ) : (
          <div className="rounded-[8px] border border-rule-200 bg-paper-50 overflow-hidden">
            <div className="hidden md:grid grid-cols-[1.5fr_1fr_120px_120px_180px_120px] px-4 py-2.5 text-[11px] uppercase tracking-[0.14em] text-ink-500 bg-cream-50 border-b border-rule-200">
              <span>File</span>
              <span>Status</span>
              <span className="text-right">Reviews</span>
              <span className="text-right">Duration</span>
              <span>Created</span>
              <span className="text-right">Actions</span>
            </div>
            <ul className="divide-y divide-rule-200">
              {analyses.map((a) => (
                <li
                  key={a.id}
                  className="grid grid-cols-1 md:grid-cols-[1.5fr_1fr_120px_120px_180px_120px] px-4 py-3 items-center gap-y-2 gap-x-3"
                >
                  <Link to={`/analyses/${a.id}`} className="flex items-center gap-3 min-w-0 hover:opacity-90">
                    <span className="grid place-items-center h-9 w-9 rounded-[4px] shrink-0 bg-cream-100 text-ink-500 shadow-[inset_0_0_0_1px_var(--rule-300)]">
                      <FileText size={15} />
                    </span>
                    <span className="min-w-0">
                      <span className="block text-sm font-medium truncate text-ink-900">{a.file_name}</span>
                      <span className="block text-xs uppercase tracking-[0.1em] text-ink-500">{a.file_format}</span>
                    </span>
                  </Link>
                  <span>
                    <StatusPill status={a.status} />
                  </span>
                  <span className="text-sm tabular-nums font-mono md:text-right text-ink-900">
                    {a.total_reviews ?? '—'}
                  </span>
                  <span className="text-sm tabular-nums font-mono md:text-right text-ink-500">
                    {fmtDuration(a.duration_ms)}
                  </span>
                  <span className="text-sm font-mono text-ink-500">{fmtDate(a.created_at)}</span>
                  <span className="flex items-center gap-1.5 md:justify-end">
                    {a.status !== 'completed' && a.status !== 'processing' && (
                      <button
                        type="button"
                        onClick={() => run(a.id)}
                        disabled={running === a.id}
                        className="btn-ghost !h-8 !px-2.5"
                        aria-label="Run analysis"
                      >
                        <Play size={13} /> {running === a.id ? 'Running…' : 'Run'}
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => remove(a.id)}
                      className="btn-ghost !h-8 !w-8 !p-0 text-ink-500 hover:text-rust-600"
                      aria-label="Delete"
                    >
                      <Trash2 size={13} />
                    </button>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>
    </div>
  )
}
