import { startTransition, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, FolderKanban, Trash2, X, Sparkles } from 'lucide-react'
import api from '../lib/api'

function fmtDate(s) {
  if (!s) return '—'
  return new Date(s).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

function ProjectSkeleton() {
  return (
    <div className="rounded-[8px] border border-rule-200 bg-paper-50 p-5">
      <div className="ed-skeleton h-4 w-32 mb-3" />
      <div className="ed-skeleton h-3 w-48 mb-2" />
      <div className="ed-skeleton h-3 w-24" />
    </div>
  )
}

function NewProjectModal({ open, onClose, onCreate }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  if (!open) return null

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await onCreate({ name: name.trim(), description: description.trim() })
      setName('')
      setDescription('')
      onClose()
    } catch (err) {
      setError(err?.message || 'Could not create project.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-40 grid place-items-center px-4 bg-black/35 backdrop-blur-[3px]"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="w-full max-w-[480px] rounded-[8px] bg-paper-50 p-6 animate-fade-in-up"
        style={{
          boxShadow:
            'inset 0 0 0 1px var(--rule-300), 0 24px 64px -32px rgb(26 23 20 / 0.18)',
        }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="np-title"
      >
        <div className="flex items-start justify-between mb-1">
          <h2 id="np-title" className="font-serif text-[28px] leading-tight text-ink-900">
            New project
          </h2>
          <button type="button" onClick={onClose} aria-label="Close" className="btn-ghost !h-8 !w-8 !p-0">
            <X size={15} />
          </button>
        </div>
        <p className="text-sm mb-5 text-ink-500">
          A project groups together review datasets and the analyses you run on them.
        </p>

        <form onSubmit={submit} className="space-y-4">
          <div>
            <label htmlFor="np-name" className="ed-label">
              Name
            </label>
            <input
              id="np-name"
              className="ed-input"
              required
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Q1 product reviews"
            />
          </div>
          <div>
            <label htmlFor="np-desc" className="ed-label">
              Description (optional)
            </label>
            <textarea
              id="np-desc"
              className="ed-input min-h-[100px] py-2.5 resize-y"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What dataset will live here?"
            />
          </div>

          {error && (
            <div className="text-xs px-3 py-2 rounded-[4px] text-rust-700 bg-rust-50 border border-rule-300">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={busy || !name.trim()} className="btn-primary">
              {busy ? 'Creating…' : 'Create project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function Projects() {
  const [projects, setProjects] = useState(null)
  const [open, setOpen] = useState(false)

  const load = async () => {
    try {
      const { data } = await api.get('/projects')
      setProjects(Array.isArray(data) ? data : data?.items || [])
    } catch {
      setProjects([])
    }
  }

  useEffect(() => {
    startTransition(() => {
      void load()
    })
  }, [])

  const create = async (payload) => {
    await api.post('/projects', payload)
    await load()
  }

  const remove = async (id) => {
    if (!confirm('Delete this project? This cannot be undone.')) return
    await api.delete(`/projects/${id}`)
    setProjects((p) => p.filter((x) => x.id !== id))
  }

  const loading = projects === null
  const empty = !loading && projects.length === 0

  return (
    <div>
      <div className="flex items-center justify-between gap-4 mb-6 flex-wrap">
        <div>
          <div className="font-mono text-xs uppercase tracking-[0.18em] text-ink-500 mb-1">Workspace</div>
          <h1 className="font-serif text-[36px] sm:text-[40px] tracking-[-0.02em] text-ink-900 flex items-center gap-3">
            Projects
            {!loading && (
              <span className="text-sm font-normal font-sans tabular-nums text-ink-500">{projects.length}</span>
            )}
          </h1>
        </div>
        <button type="button" onClick={() => setOpen(true)} className="btn-primary">
          <Plus size={15} /> New project
        </button>
      </div>

      {loading && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <ProjectSkeleton key={i} />
          ))}
        </div>
      )}

      {empty && (
        <div className="rounded-[8px] border border-rule-300 bg-cream-50/80 p-12 text-center">
          <div className="mx-auto h-14 w-14 grid place-items-center rounded-[4px] mb-4 bg-accent-50 text-accent-700 shadow-[inset_0_0_0_1px_var(--rule-300)]">
            <Sparkles size={22} />
          </div>
          <h2 className="font-serif text-[28px] text-ink-900 mb-2">Your first project awaits</h2>
          <p className="text-sm mb-6 max-w-md mx-auto text-ink-500">
            Create a project to upload review datasets and run sentiment, aspect, topic and keyword analyses.
          </p>
          <button type="button" onClick={() => setOpen(true)} className="btn-primary">
            <Plus size={15} /> New project
          </button>
        </div>
      )}

      {!loading && !empty && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((p) => (
            <Link
              key={p.id}
              to={`/projects/${p.id}`}
              className="rounded-[8px] border border-rule-200 bg-paper-50 p-5 group block hover:bg-cream-50/70 transition-colors"
            >
              <div className="flex items-start gap-3">
                <span className="grid place-items-center h-10 w-10 rounded-[4px] shrink-0 bg-cream-100 text-accent-600 shadow-[inset_0_0_0_1px_var(--rule-300)]">
                  <FolderKanban size={17} />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="font-sans font-semibold truncate text-ink-900">{p.name}</div>
                  <div className="text-xs mt-0.5 text-ink-500 tabular-nums">Created {fmtDate(p.created_at)}</div>
                </div>
                <button
                  type="button"
                  aria-label="Delete project"
                  className="btn-ghost !h-8 !w-8 !p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                  onClick={(e) => {
                    e.preventDefault()
                    remove(p.id)
                  }}
                >
                  <Trash2 size={14} />
                </button>
              </div>
              {p.description && <p className="text-sm mt-3 line-clamp-3 text-ink-600">{p.description}</p>}
            </Link>
          ))}
        </div>
      )}

      <NewProjectModal open={open} onClose={() => setOpen(false)} onCreate={create} />
    </div>
  )
}
