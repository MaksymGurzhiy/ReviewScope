import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ScanText, Mail, Lock, ArrowRight } from 'lucide-react'
import { useAuth } from '../lib/auth'

export default function Login() {
  const { signIn } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await signIn(email, password)
      navigate('/projects')
    } catch (err) {
      setError(err?.message || 'Sign in failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-paper-50 grid lg:grid-cols-2">
      <aside className="hidden lg:flex flex-col justify-between p-12 border-r border-rule-200 bg-cream-50">
        <div>
          <p className="font-serif italic text-xl text-ink-900 leading-snug max-w-[28ch]">
            Turn scattered reviews into a single, readable verdict.
          </p>
          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-ink-500 mt-6">ReviewScope</p>
        </div>
        <p className="font-serif text-[15px] text-ink-600 italic">Paper &amp; ink, not dashboards.</p>
      </aside>

      <div className="grid place-items-center px-4 py-10">
        <div className="w-full max-w-[420px] animate-fade-in-up">
          <div className="flex items-center justify-center gap-2 mb-7">
            <span className="grid place-items-center h-9 w-9 rounded-[4px] bg-accent-600 text-paper-50">
              <ScanText size={18} strokeWidth={2.25} />
            </span>
            <span className="font-serif font-medium text-xl tracking-tight text-ink-900">
              ReviewScope<span className="text-accent-600">.</span>
            </span>
          </div>

          <div
            className="rounded-[8px] bg-paper-50 p-7"
            style={{
              boxShadow:
                'inset 0 0 0 1px var(--rule-300), 0 24px 64px -32px rgb(26 23 20 / 0.12)',
            }}
          >
            <div className="font-mono text-xs text-accent-600 tracking-[0.06em] uppercase">Auth</div>
            <h1 className="font-serif text-[32px] leading-tight text-ink-900 mt-2 mb-1">Welcome back</h1>
            <p className="text-sm mb-6 text-ink-500">Sign in to continue analyzing customer reviews.</p>

            <form onSubmit={submit} className="space-y-4">
              <div>
                <label htmlFor="email" className="ed-label">
                  Email
                </label>
                <div className="relative">
                  <Mail
                    size={15}
                    className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none text-ink-400"
                  />
                  <input
                    id="email"
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="ed-input pl-9"
                    placeholder="you@university.edu"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="password" className="ed-label">
                  Password
                </label>
                <div className="relative">
                  <Lock
                    size={15}
                    className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none text-ink-400"
                  />
                  <input
                    id="password"
                    type="password"
                    autoComplete="current-password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="ed-input pl-9"
                    placeholder="••••••••"
                  />
                </div>
              </div>

              {error && (
                <div className="text-xs px-3 py-2 rounded-[4px] text-rust-700 bg-rust-50 border border-rule-300">
                  {error}
                </div>
              )}

              <button type="submit" disabled={busy} className="btn-primary w-full !h-11">
                {busy ? 'Signing in…' : (
                  <>
                    Sign in <ArrowRight size={15} />
                  </>
                )}
              </button>
            </form>

            <div className="mt-6 text-sm text-center text-ink-500">
              New to ReviewScope?{' '}
              <Link to="/register" className="text-accent-600 hover:text-accent-700 underline underline-offset-2">
                Create an account
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
