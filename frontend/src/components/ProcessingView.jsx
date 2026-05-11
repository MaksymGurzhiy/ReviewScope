import { useEffect, useState } from 'react'
import {
  FileSearch, Languages, Smile, Tag, Layers, Hash,
  Lightbulb, Save, Check, Loader2, AlertCircle,
} from 'lucide-react'

const STAGES = [
  { key: 'parsing', label: 'Parsing review file', icon: FileSearch, range: [0, 4] },
  { key: 'language_detection', label: 'Detecting languages', icon: Languages, range: [4, 14] },
  { key: 'sentiment', label: 'Sentiment analysis (BERT)', icon: Smile, range: [14, 44] },
  { key: 'aspects', label: 'Aspect-based sentiment (spaCy)', icon: Tag, range: [44, 59] },
  { key: 'topics', label: 'Topic modeling (BERTopic)', icon: Layers, range: [59, 77] },
  { key: 'keywords', label: 'Key phrases (log-odds ratio)', icon: Hash, range: [77, 89] },
  { key: 'insights', label: 'Insights & summary', icon: Lightbulb, range: [89, 97] },
  { key: 'saving', label: 'Saving results', icon: Save, range: [97, 100] },
]

function fmtElapsed(ms) {
  if (ms < 1000) return `${ms} ms`
  const s = Math.floor(ms / 1000)
  if (s < 60) return `${s}s`
  return `${Math.floor(s / 60)}m ${s % 60}s`
}

export default function ProcessingView({ analysis }) {
  const [now, setNow] = useState(0)

  useEffect(() => {
    const tick = () => setNow(Date.now())
    tick()
    const t = setInterval(tick, 1000)
    return () => clearInterval(t)
  }, [])

  const pct = Math.max(0, Math.min(100, analysis?.progress_pct ?? 0))
  const stageKey = analysis?.progress_stage
  const failed = analysis?.status === 'failed'
  const startedAt = analysis?.created_at ? new Date(analysis.created_at).getTime() : now
  const elapsed = Math.max(0, now - startedAt)

  const currentIdx = (() => {
    if (stageKey) {
      const i = STAGES.findIndex((s) => s.key === stageKey)
      if (i >= 0) return i
    }
    return STAGES.findIndex((s) => pct < s.range[1])
  })()

  return (
    <div className="rounded-[8px] bg-paper-100 shadow-[inset_0_0_0_1px_var(--rule-200)] p-7 animate-[fade-in-up_220ms_ease-out_both]">
      <div className="flex items-start justify-between gap-4 mb-5 flex-wrap">
        <div className="flex items-center gap-3">
          <span
            className={`grid place-items-center h-10 w-10 rounded-[4px] ${
              failed ? 'bg-rust-50 text-rust-600' : 'bg-accent-50 text-accent-600'
            }`}
          >
            {failed ? <AlertCircle size={18} /> : <Loader2 size={18} className="animate-spin" />}
          </span>
          <div>
            <div className="font-sans text-[11px] font-medium uppercase tracking-[0.18em] text-ink-500 mb-0.5">
              {failed ? 'Failed' : 'Analysis in progress'}
            </div>
            <h2 className="font-serif text-xl text-ink-900">
              {failed ? 'The pipeline could not complete' : 'Crunching your reviews…'}
            </h2>
          </div>
        </div>
        <div className="text-right">
          <div className="font-mono text-[28px] tabular-nums text-ink-900">{pct}%</div>
          <div className="font-sans text-xs text-ink-500">elapsed {fmtElapsed(elapsed)}</div>
        </div>
      </div>

      <div className="h-2 w-full rounded-full mb-6 bg-rule-200 overflow-hidden">
        <div
          className={`h-full rounded-full transition-[width] duration-500 ${failed ? 'bg-rust-500' : 'bg-accent-600'}`}
          style={{ width: `${pct}%` }}
        />
      </div>

      <ul className="space-y-1">
        {STAGES.map((stage, i) => {
          const { key, label, icon: StageIcon, range } = stage
          const isDone = pct >= range[1] || (failed && i < currentIdx)
          const isActive = !failed && !isDone && i === currentIdx

          const iconTone = failed && i === currentIdx
            ? 'bg-rust-50 text-rust-600'
            : isDone
              ? 'bg-moss-50 text-moss-600'
              : isActive
                ? 'bg-accent-50 text-accent-600'
                : 'bg-cream-50 text-ink-400'

          return (
            <li
              key={key}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-[4px] transition-colors ${
                isActive ? 'bg-cream-50' : ''
              }`}
            >
              <span className={`grid place-items-center h-8 w-8 rounded-[4px] flex-shrink-0 ${iconTone}`}>
                {isDone ? (
                  <Check size={15} />
                ) : isActive ? (
                  <Loader2 size={15} className="animate-spin" />
                ) : (
                  <StageIcon size={15} />
                )}
              </span>
              <span
                className={`flex-1 text-sm ${isDone || isActive ? 'text-ink-900 font-medium' : 'text-ink-500'}`}
              >
                {label}
              </span>
              {isActive && (
                <span className="text-xs tabular-nums font-mono text-accent-600">running</span>
              )}
              {isDone && <span className="text-xs tabular-nums font-mono text-moss-600">done</span>}
            </li>
          )
        })}
      </ul>

      {failed && analysis?.error_message && (
        <div className="mt-5 text-xs px-3 py-2 rounded-[4px] bg-rust-50 text-rust-700 border border-rule-300">
          {analysis.error_message}
        </div>
      )}

      {!failed && (
        <p className="mt-5 text-xs text-ink-500">
          Transformer models download on first run — plan for ~1&nbsp;minute. Later runs reuse the cache.
        </p>
      )}
    </div>
  )
}
