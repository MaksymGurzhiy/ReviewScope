import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  ArrowDownRight,
  ArrowUpRight,
  Copy,
  Check,
  Download,
  FileSpreadsheet,
  Minus,
  Play,
  Quote,
  AlertTriangle,
} from 'lucide-react'
import api from '../lib/api'
import StatusPill from '../components/StatusPill'
import ProcessingView from '../components/ProcessingView'

function verdictFor(s) {
  if (!s)
    return {
      key: 'pending',
      label: 'Pending',
      tone: 'rule',
      line: 'Run the analysis to surface a verdict.',
    }
  const pos = s.positive_percent ?? 0
  const neg = s.negative_percent ?? 0
  if (pos >= 75)
    return {
      key: 'star',
      label: 'Star',
      tone: 'moss',
      line: 'Customers are overwhelmingly satisfied. Lean into what works.',
    }
  if (pos >= 55 && neg < 20)
    return {
      key: 'strength',
      label: 'Strength',
      tone: 'moss',
      line: 'A clear positive lean with isolated issues worth tracking.',
    }
  if (Math.abs(pos - neg) < 12)
    return {
      key: 'split',
      label: 'Split',
      tone: 'ochre',
      line: 'Reviews are divided. The next action depends on which segment matters more.',
    }
  if (neg >= 40 && neg < 60)
    return {
      key: 'weakness',
      label: 'Weakness',
      tone: 'rust',
      line: 'Negative sentiment is loud enough to demand a response, not a deflection.',
    }
  if (neg >= 60)
    return {
      key: 'critical',
      label: 'Critical',
      tone: 'rust',
      line: 'This product is failing its customers. Treat the recommendations as triage.',
    }
  return {
    key: 'neutral',
    label: 'Mixed',
    tone: 'ochre',
    line: 'No dominant signal. Read the aspects section before drawing conclusions.',
  }
}

const TONE_BG = {
  moss: 'bg-moss-50 text-moss-900 shadow-[inset_0_0_0_1px_var(--moss-200)]',
  ochre: 'bg-ochre-50 text-ochre-900 shadow-[inset_0_0_0_1px_var(--ochre-700)]',
  rust: 'bg-rust-50 text-rust-900 shadow-[inset_0_0_0_1px_var(--rust-200)]',
  rule: 'bg-cream-100 text-ink-900 shadow-[inset_0_0_0_1px_var(--rule-300)]',
}
const SENT_DOT = {
  POSITIVE: 'bg-moss-500',
  positive: 'bg-moss-500',
  NEUTRAL: 'bg-ochre-500',
  neutral: 'bg-ochre-500',
  NEGATIVE: 'bg-rust-500',
  negative: 'bg-rust-500',
}
const SENT_TEXT = {
  POSITIVE: 'text-moss-700',
  positive: 'text-moss-700',
  NEUTRAL: 'text-ochre-700',
  neutral: 'text-ochre-700',
  NEGATIVE: 'text-rust-700',
  negative: 'text-rust-700',
}

function MastheadBreadcrumb({ projectName, projectId, fileName }) {
  return (
    <nav className="font-sans text-xs uppercase tracking-[0.14em] text-ink-500 flex items-center gap-2 flex-wrap justify-end">
      <Link to="/projects" className="hover:text-ink-900 transition-colors">
        Projects
      </Link>
      <span aria-hidden>/</span>
      {projectId ? (
        <Link to={`/projects/${projectId}`} className="hover:text-ink-900 transition-colors">
          {projectName}
        </Link>
      ) : (
        <span>{projectName}</span>
      )}
      <span aria-hidden>/</span>
      <span className="text-ink-900 normal-case tracking-normal truncate max-w-[200px] sm:max-w-xs">
        {fileName}
      </span>
    </nav>
  )
}

function MetaDot({ label, value }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="font-sans text-[10px] uppercase tracking-[0.18em] text-ink-500">{label}</span>
      <span className="font-mono text-[15px] text-ink-900 tabular-nums">{value}</span>
    </div>
  )
}

function PullQuote({ tone = 'rule', kicker, children }) {
  const accent = {
    moss: 'before:bg-moss-500 text-moss-900',
    ochre: 'before:bg-ochre-500 text-ochre-900',
    rust: 'before:bg-rust-500 text-rust-900',
    rule: 'before:bg-ink-900 text-ink-900',
  }[tone]
  return (
    <figure
      className={`relative pl-6 py-2 before:absolute before:left-0 before:top-1 before:bottom-1 before:w-[3px] ${accent}`}
    >
      {kicker && (
        <figcaption className="font-sans text-[10px] uppercase tracking-[0.18em] text-ink-500 mb-1">
          {kicker}
        </figcaption>
      )}
      <blockquote className="font-serif text-[19px] leading-[1.45] text-ink-900">{children}</blockquote>
    </figure>
  )
}

function CopyVerdict({ text }) {
  const [done, setDone] = useState(false)
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text || '')
          setDone(true)
          setTimeout(() => setDone(false), 1400)
        } catch {
          /* clipboard unavailable */
        }
      }}
      className="inline-flex items-center gap-1.5 font-sans text-[12px] text-ink-500 hover:text-ink-900 transition-colors focus-ring rounded-sm"
    >
      {done ? <Check size={13} /> : <Copy size={13} />}
      {done ? 'Copied' : 'Copy verdict'}
    </button>
  )
}

function VerdictMasthead({ verdict, sentiment, total, duration, language }) {
  return (
    <section
      aria-labelledby="verdict-h"
      className="relative border-t border-b border-ink-900 bg-cream-50"
    >
      <div className="mx-auto max-w-[1240px] px-6 lg:px-10 py-10 lg:py-14 grid lg:grid-cols-[1.4fr_1fr] gap-10 items-end">
        <div>
          <div
            className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-[4px] font-sans text-[11px] uppercase tracking-[0.18em] ${TONE_BG[verdict.tone]}`}
          >
            <span className="font-mono">Verdict</span>
            <span aria-hidden>·</span>
            <span className="font-medium">{verdict.label}</span>
          </div>

          <h1
            id="verdict-h"
            className="font-serif text-[52px] sm:text-[76px] lg:text-[104px] leading-[0.92] tracking-[-0.025em] text-ink-900 mt-6"
          >
            {verdict.label}.
          </h1>

          <p className="font-serif italic text-[22px] lg:text-[26px] leading-[1.4] text-ink-700 mt-5 max-w-[40ch]">
            {verdict.line}
          </p>

          <div className="mt-6">
            <CopyVerdict text={`${verdict.label}: ${verdict.line}`} />
          </div>
        </div>

        <dl className="grid grid-cols-2 gap-x-8 gap-y-5 border-t border-rule-300 pt-6 lg:border-t-0 lg:pt-0 lg:border-l lg:border-rule-300 lg:pl-10">
          <MetaDot label="Reviews" value={total ? total.toLocaleString() : '—'} />
          <MetaDot label="Runtime" value={duration || '—'} />
          <MetaDot label="Language" value={language || '—'} />
          <MetaDot label="Positive" value={sentiment ? `${sentiment.positive_percent ?? 0}%` : '—'} />
          <MetaDot label="Neutral" value={sentiment ? `${sentiment.neutral_percent ?? 0}%` : '—'} />
          <MetaDot label="Negative" value={sentiment ? `${sentiment.negative_percent ?? 0}%` : '—'} />
        </dl>
      </div>
    </section>
  )
}

function SentimentDonut({ sentiment }) {
  const pos = sentiment?.positive_percent ?? 0
  const neu = sentiment?.neutral_percent ?? 0
  const neg = sentiment?.negative_percent ?? 0
  const total = sentiment?.total ?? 0
  const r = 78
  const c = 2 * Math.PI * r
  const seg = (p) => (p / 100) * c
  let offset = 0
  const arcs = [
    {
      color: 'var(--moss-600)',
      pct: pos,
      label: 'Positive',
      n: sentiment?.positive,
    },
    {
      color: 'var(--ochre-500)',
      pct: neu,
      label: 'Neutral',
      n: sentiment?.neutral,
    },
    {
      color: 'var(--rust-600)',
      pct: neg,
      label: 'Negative',
      n: sentiment?.negative,
    },
  ]

  return (
    <div className="grid sm:grid-cols-[220px_1fr] gap-8 items-center">
      <div className="relative w-[220px] h-[220px] mx-auto sm:mx-0">
        <svg viewBox="0 0 200 200" className="w-full h-full -rotate-90">
          <circle cx="100" cy="100" r={r} fill="none" stroke="var(--rule-200)" strokeWidth="18" />
          {arcs.map((a, i) => {
            const len = seg(a.pct)
            const el = (
              <circle
                key={i}
                cx="100"
                cy="100"
                r={r}
                fill="none"
                stroke={a.color}
                strokeWidth="18"
                strokeDasharray={`${len} ${c - len}`}
                strokeDashoffset={-offset}
              />
            )
            offset += len
            return el
          })}
        </svg>
        <div className="absolute inset-0 grid place-items-center text-center pointer-events-none">
          <div>
            <div className="font-serif text-[52px] leading-none text-ink-900 tracking-[-0.02em] tabular-nums">
              {pos}
            </div>
            <div className="font-sans text-[11px] uppercase tracking-[0.18em] text-ink-500 mt-1">
              percent positive
            </div>
          </div>
        </div>
      </div>

      <ul className="space-y-3.5">
        {arcs.map((a) => (
          <li key={a.label} className="flex items-baseline gap-3 flex-wrap">
            <span className="w-2.5 h-2.5 rounded-full mt-1 shrink-0" style={{ background: a.color }} />
            <span className="font-sans text-sm text-ink-900 w-20">{a.label}</span>
            <span className="font-mono text-sm text-ink-900 tabular-nums w-12 text-right">{a.pct}%</span>
            <span className="font-mono text-xs text-ink-500 tabular-nums">
              {a.n ?? '—'} of {total ? total.toLocaleString() : '—'}
            </span>
          </li>
        ))}
        <li className="pt-2 border-t border-rule-200">
          <p className="font-serif italic text-[15px] leading-snug text-ink-700">
            {pos >= 60 &&
              'Praise dominates the distribution; treat negatives as edge cases worth resolving.'}
            {pos >= 40 &&
              pos < 60 &&
              'A working majority is satisfied, but the negative tail is large enough to compound.'}
            {pos < 40 && 'Negative volume is structural here, not anecdotal. Read aspects below carefully.'}
          </p>
        </li>
      </ul>
    </div>
  )
}

function AspectAnnotatedChart({ aspects }) {
  const list = (aspects?.aspects || [])
    .slice(0, 12)
    .map((a) => {
      const total = a.total_mentions || a.positive + a.negative + a.neutral || 1
      const score = Math.round(((a.positive - a.negative) / total) * 100)
      const praise =
        (a.praise_words || a.opinions_positive || a.context_positive || a.positive_words || []).slice(0, 3)
      const complaints =
        (
          a.complaint_words ||
          a.opinions_negative ||
          a.context_negative ||
          a.negative_words ||
          []
        ).slice(0, 3)
      return { aspect: a.aspect, score, mentions: total, praise, complaints }
    })
    .sort((x, y) => Math.abs(y.score) - Math.abs(x.score))

  if (!list.length) {
    return <p className="font-serif italic text-ink-500">No aspects extracted from this dataset.</p>
  }

  return (
    <div className="space-y-1">
      {list.map((a) => {
        const positive = a.score >= 0
        const width = Math.min(Math.abs(a.score), 100)
        return (
          <article
            key={a.aspect}
            className="grid grid-cols-1 sm:grid-cols-[160px_1fr] lg:grid-cols-[180px_1fr] gap-6 py-4 border-t border-rule-200 first:border-t-0"
          >
            <header className="flex flex-col">
              <h3 className="font-serif text-xl leading-tight text-ink-900">{a.aspect}</h3>
              <span className="font-mono text-[11px] text-ink-500 tabular-nums mt-1">
                {a.mentions} mentions · net {a.score > 0 ? '+' : ''}
                {a.score}
              </span>
            </header>

            <div>
              <div className="relative h-2.5">
                <div className="absolute left-1/2 top-0 bottom-0 w-px bg-ink-900/40" />
                {positive ? (
                  <div
                    className="absolute left-1/2 top-0 bottom-0 bg-moss-500"
                    style={{ width: `${width / 2}%` }}
                  />
                ) : (
                  <div
                    className="absolute right-1/2 top-0 bottom-0 bg-rust-500"
                    style={{ width: `${width / 2}%` }}
                  />
                )}
              </div>
              <p className="font-serif text-[14.5px] leading-[1.55] text-ink-700 mt-3">
                {a.praise.length > 0 && (
                  <>
                    <span className="font-sans text-[10px] uppercase tracking-[0.18em] text-moss-700 mr-1.5">
                      Praise
                    </span>
                    <span className="text-moss-800">{a.praise.join(', ')}</span>
                  </>
                )}
                {a.praise.length > 0 && a.complaints.length > 0 && (
                  <span className="mx-2 text-ink-400">·</span>
                )}
                {a.complaints.length > 0 && (
                  <>
                    <span className="font-sans text-[10px] uppercase tracking-[0.18em] text-rust-700 mr-1.5">
                      Complaints
                    </span>
                    <span className="text-rust-800">{a.complaints.join(', ')}</span>
                  </>
                )}
              </p>
            </div>
          </article>
        )
      })}
    </div>
  )
}

function KeywordBands({ keywords }) {
  if (!keywords) return null
  const bands = [
    { tone: 'moss', kicker: '4–5 stars', label: 'Why customers love it', items: keywords.positive_keywords || [] },
    { tone: 'ochre', kicker: '3 stars', label: 'Where they hesitate', items: keywords.neutral_keywords || [] },
    { tone: 'rust', kicker: '1–2 stars', label: 'Why they walk away', items: keywords.negative_keywords || [] },
  ]

  return (
    <div className="grid md:grid-cols-3 gap-x-10 gap-y-8">
      {bands.map((b) => (
        <section key={b.tone} className="space-y-4">
          <header>
            <div
              className={`font-sans text-[10px] uppercase tracking-[0.2em] mb-1 ${
                b.tone === 'moss' ? 'text-moss-700' : b.tone === 'rust' ? 'text-rust-700' : 'text-ochre-700'
              }`}
            >
              {b.kicker}
            </div>
            <h3 className="font-serif text-[22px] leading-snug text-ink-900">{b.label}</h3>
          </header>

          {b.items.length === 0 ? (
            <p className="font-serif italic text-ink-500">No phrases surfaced in this bucket.</p>
          ) : (
            <ol className="space-y-3">
              {b.items.slice(0, 8).map((item, i) => {
                const tuple = Array.isArray(item)
                const phrase = tuple ? item[0] : item?.phrase ?? item
                const score = tuple ? item[1] : item?.score
                return (
                  <li key={`${phrase}-${i}`} className="flex items-baseline gap-3">
                    <span className="font-mono text-[11px] text-ink-400 tabular-nums w-6 shrink-0">
                      {String(i + 1).padStart(2, '0')}
                    </span>
                    <span className="font-serif text-lg leading-snug text-ink-900 flex-1">
                      &ldquo;{phrase}&rdquo;
                    </span>
                    {score != null && (
                      <span className="font-mono text-[11px] text-ink-500 tabular-nums shrink-0">
                        {typeof score === 'number' ? score.toFixed(2) : score}
                      </span>
                    )}
                  </li>
                )
              })}
            </ol>
          )}
        </section>
      ))}
    </div>
  )
}

function TopicsDek({ topics }) {
  const list = topics?.topics || []
  if (!list.length) {
    return (
      <p className="font-serif italic text-ink-500">
        Topic modeling found no coherent clusters — likely too few or too uniform reviews.
      </p>
    )
  }
  return (
    <ol className="grid md:grid-cols-2 gap-x-10">
      {list.slice(0, 8).map((t, idx) => (
        <li
          key={t.topic_id ?? t.id ?? idx}
          className="grid grid-cols-[36px_1fr] gap-4 py-5 border-t border-rule-200 first:border-t-0 md:border-t md:[&:nth-child(-n+2)]:border-t-0"
        >
          <span className="font-serif text-[28px] leading-none text-accent-600 tabular-nums">
            {String(idx + 1).padStart(2, '0')}
          </span>
          <div>
            <h4 className="font-serif text-[17px] leading-snug text-ink-900 mb-1">
              {t.label || t.name || `Theme ${idx + 1}`}
            </h4>
            <p className="font-sans text-[13px] text-ink-600 leading-relaxed">
              {(t.keywords || []).slice(0, 8).join(' · ')}
            </p>
            <span className="font-mono text-[11px] text-ink-500 tabular-nums mt-2 inline-block">
              {t.count} reviews
            </span>
          </div>
        </li>
      ))}
    </ol>
  )
}

function SampleCards({ samples }) {
  if (!samples?.length) return null
  const normSent = (s) =>
    String(s || 'neutral').toLowerCase() === 'positive'
      ? 'positive'
      : String(s || 'neutral').toLowerCase() === 'negative'
        ? 'negative'
        : 'neutral'
  return (
    <div className="grid md:grid-cols-2 gap-x-10 gap-y-8">
      {samples.slice(0, 8).map((r, i) => {
        const sentiment = normSent(r.sentiment)
        const sideColor =
          sentiment === 'positive' ? 'border-moss-500' : sentiment === 'negative' ? 'border-rust-500' : 'border-ochre-500'
        const Icon = sentiment === 'positive' ? ArrowUpRight : sentiment === 'negative' ? ArrowDownRight : Minus
        const text = r.text || r.review_text || ''
        const aspects = r.aspects
        return (
          <article key={r.id ?? i} className={`pl-6 border-l-2 ${sideColor}`}>
            <header className="flex items-baseline justify-between mb-3 gap-3">
              <span className="font-mono text-[11px] text-ink-500 tabular-nums">
                #{String(i + 1).padStart(3, '0')} · {(r.language || '—').toUpperCase()}
              </span>
              <span
                className={`inline-flex items-center gap-1 font-sans text-[11px] uppercase tracking-[0.16em] ${SENT_TEXT[sentiment]}`}
              >
                <Icon size={12} /> {sentiment}
                {typeof r.rating === 'number' && (
                  <span className="ml-2 font-mono text-ink-500">{r.rating}/5</span>
                )}
              </span>
            </header>

            <blockquote className="font-serif text-lg leading-relaxed text-ink-900">
              <Quote className="inline -mt-2 mr-1 text-ink-300 shrink-0" size={14} aria-hidden />
              {text}
            </blockquote>

            {aspects && typeof aspects === 'object' && !Array.isArray(aspects) && Object.keys(aspects).length > 0 && (
              <footer className="mt-4 flex flex-wrap gap-x-3 gap-y-1">
                {Object.entries(aspects)
                  .slice(0, 6)
                  .map(([aspect, p]) => {
                    const tone = typeof p === 'string' ? normSent(p) : 'neutral'
                    return (
                      <span key={aspect} className="inline-flex items-center gap-1.5 font-sans text-xs">
                        <span className={`w-1.5 h-1.5 rounded-full ${SENT_DOT[tone] || 'bg-ink-400'}`} />
                        <span className="text-ink-700">{aspect}</span>
                      </span>
                    )
                  })}
              </footer>
            )}
          </article>
        )
      })}
    </div>
  )
}

function parseConclusion(summaryText) {
  if (!summaryText) return null
  const idx = summaryText.indexOf('CONCLUSION')
  if (idx === -1) return null
  let rest = summaryText.slice(idx + 'CONCLUSION'.length)
  if (rest.startsWith('\n')) rest = rest.slice(1)
  if (rest.startsWith('=')) {
    const nl = rest.indexOf('\n')
    if (nl !== -1) rest = rest.slice(nl + 1)
  }

  const out = { verdict: '', strengths: [], needsWork: [], actions: [] }
  let mode = 'verdict'
  let current = null

  for (const raw of rest.split('\n')) {
    const line = raw.replace(/\s+$/, '')
    if (!line.trim()) continue
    if (/^STRENGTHS\b/i.test(line.trim())) { mode = 'strengths'; current = null; continue }
    if (/^NEEDS WORK\b/i.test(line.trim())) { mode = 'problems'; current = null; continue }
    if (/^WHAT TO DO NEXT/i.test(line.trim())) { mode = 'actions'; current = null; continue }
    if (/^No recurring problems/i.test(line.trim())) { mode = 'noop'; continue }

    if (mode === 'verdict') {
      out.verdict += (out.verdict ? ' ' : '') + line.trim()
      continue
    }

    const bullet = line.match(/^\s*-\s+(.+)$/)
    const example = line.match(/^\s+(Example review|Praise example|Complaint example|Example complaint):\s*"(.*)"\s*$/)
    const action = line.match(/^\s*(\d+)\.\s+(.+)$/)

    if ((mode === 'strengths' || mode === 'problems') && bullet) {
      current = { sentence: bullet[1] }
      ;(mode === 'strengths' ? out.strengths : out.needsWork).push(current)
    } else if (mode === 'actions' && action) {
      out.actions.push(action[2])
    } else if (mode === 'actions' && bullet) {
      out.actions.push(bullet[1])
    } else if (example && current) {
      const kind = example[1].toLowerCase()
      if (kind.includes('praise')) current.examplePraise = example[2]
      else if (kind.includes('complaint')) current.exampleComplaint = example[2]
      else current.exampleReview = example[2]
    }
  }

  if (!out.verdict && !out.strengths.length && !out.needsWork.length && !out.actions.length) {
    return null
  }
  return out
}

function NarrativeBrief({ data, verdictTone = 'rule' }) {
  const toneAccent = {
    moss: 'before:bg-moss-500 text-moss-900',
    ochre: 'before:bg-ochre-500 text-ochre-900',
    rust: 'before:bg-rust-500 text-rust-900',
    rule: 'before:bg-ink-900 text-ink-900',
  }[verdictTone]

  return (
    <div className="grid lg:grid-cols-[1fr_1fr] gap-x-12 gap-y-12">
      {data.verdict && (
        <figure
          className={`relative pl-7 py-2 lg:col-span-2 before:absolute before:left-0 before:top-1 before:bottom-1 before:w-[4px] ${toneAccent}`}
        >
          <figcaption className="font-sans text-[10px] uppercase tracking-[0.2em] text-ink-500 mb-2">
            Quick verdict
          </figcaption>
          <blockquote className="font-serif text-[24px] sm:text-[28px] leading-[1.35] text-ink-900">
            {data.verdict}
          </blockquote>
        </figure>
      )}

      {data.strengths.length > 0 && (
        <section>
          <header className="mb-6">
            <div className="font-sans text-[10px] uppercase tracking-[0.2em] text-moss-700">
              Strengths
            </div>
            <h3 className="font-serif text-[26px] leading-tight text-ink-900 mt-1">
              Keep doing these
            </h3>
          </header>
          <ol className="space-y-6">
            {data.strengths.map((s, i) => (
              <li key={`s-${i}`} className="grid grid-cols-[36px_1fr] gap-3 items-baseline">
                <span className="font-serif text-[26px] leading-none text-moss-700 tabular-nums">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <div>
                  <p className="font-serif text-[17px] leading-[1.5] text-ink-900">
                    {s.sentence}
                  </p>
                  {s.exampleReview && (
                    <blockquote className="mt-3 pl-3 border-l-2 border-moss-500 font-serif italic text-[14.5px] leading-snug text-ink-600">
                      &ldquo;{s.exampleReview}&rdquo;
                    </blockquote>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </section>
      )}

      {data.needsWork.length > 0 && (
        <section>
          <header className="mb-6">
            <div className="font-sans text-[10px] uppercase tracking-[0.2em] text-rust-700">
              Needs work
            </div>
            <h3 className="font-serif text-[26px] leading-tight text-ink-900 mt-1">
              Opinions are split or negative
            </h3>
          </header>
          <ol className="space-y-6">
            {data.needsWork.map((p, i) => (
              <li key={`p-${i}`} className="grid grid-cols-[36px_1fr] gap-3 items-baseline">
                <span className="font-serif text-[26px] leading-none text-rust-700 tabular-nums">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <div>
                  <p className="font-serif text-[17px] leading-[1.5] text-ink-900">
                    {p.sentence}
                  </p>
                  {p.examplePraise && (
                    <blockquote className="mt-3 pl-3 border-l-2 border-moss-500 font-serif italic text-[14.5px] leading-snug text-ink-600">
                      <span className="font-sans not-italic text-[10px] uppercase tracking-[0.18em] text-moss-700 mr-2">
                        Praise
                      </span>
                      &ldquo;{p.examplePraise}&rdquo;
                    </blockquote>
                  )}
                  {p.exampleComplaint && (
                    <blockquote className="mt-2 pl-3 border-l-2 border-rust-500 font-serif italic text-[14.5px] leading-snug text-ink-600">
                      <span className="font-sans not-italic text-[10px] uppercase tracking-[0.18em] text-rust-700 mr-2">
                        Complaint
                      </span>
                      &ldquo;{p.exampleComplaint}&rdquo;
                    </blockquote>
                  )}
                  {!p.examplePraise && !p.exampleComplaint && p.exampleReview && (
                    <blockquote className="mt-3 pl-3 border-l-2 border-rule-300 font-serif italic text-[14.5px] leading-snug text-ink-600">
                      &ldquo;{p.exampleReview}&rdquo;
                    </blockquote>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </section>
      )}

      {data.actions.length > 0 && (
        <section className="lg:col-span-2 border-t border-rule-200 pt-10">
          <header className="mb-6">
            <div className="font-sans text-[10px] uppercase tracking-[0.2em] text-accent-600">
              What to do next
            </div>
            <h3 className="font-serif text-[28px] leading-tight text-ink-900 mt-1">
              Concrete next steps, ranked by impact
            </h3>
          </header>
          <ol className="space-y-5 max-w-[78ch]">
            {data.actions.map((act, i) => (
              <li key={`a-${i}`} className="grid grid-cols-[48px_1fr] gap-4 items-baseline">
                <span className="font-serif text-[36px] leading-none text-accent-600 tabular-nums">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <p className="font-serif text-[18px] leading-[1.5] text-ink-900">
                  {act}
                </p>
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  )
}

function pickAspectStories(aspects, side, n = 4) {
  const list = aspects?.aspects || []
  const enriched = list.map((a) => {
    const total = a.total_mentions || a.positive + a.negative + a.neutral || 1
    const score = (a.positive - a.negative) / total
    const praise = (a.praise_words || a.opinions_positive || a.context_positive || a.positive_words || []).slice(0, 3)
    const complaints = (a.complaint_words || a.opinions_negative || a.context_negative || a.negative_words || []).slice(0, 3)
    return { aspect: a.aspect, score, total, praise, complaints }
  })
  if (side === 'good') {
    return enriched
      .filter((a) => a.score > 0.05 && a.praise.length > 0)
      .sort((x, y) => y.score - x.score || y.total - x.total)
      .slice(0, n)
  }
  return enriched
    .filter((a) => a.score < -0.05 && a.complaints.length > 0)
    .sort((x, y) => x.score - y.score || y.total - x.total)
    .slice(0, n)
}

function AspectStoryList({ items, tone }) {
  if (!items?.length) {
    return (
      <p className="font-serif italic text-ink-500">
        {tone === 'rust' ? 'No standout complaints surfaced.' : 'No standout praise surfaced.'}
      </p>
    )
  }
  const accentText = tone === 'rust' ? 'text-rust-700' : 'text-moss-700'
  const phraseText = tone === 'rust' ? 'text-rust-800' : 'text-moss-800'
  const kicker = tone === 'rust' ? 'Customers complain about' : 'Customers praise'
  return (
    <ol className="space-y-7 max-w-[68ch]">
      {items.map((a, i) => {
        const phrases = tone === 'rust' ? a.complaints : a.praise
        const pct = Math.round(Math.abs(a.score) * 100)
        return (
          <li key={a.aspect} className="grid grid-cols-[44px_1fr] gap-4 items-baseline">
            <span className={`font-serif text-[34px] leading-none tabular-nums ${accentText}`}>
              {String(i + 1).padStart(2, '0')}
            </span>
            <div>
              <h4 className="font-serif text-[22px] leading-snug text-ink-900">
                {a.aspect}
              </h4>
              <p className="font-serif text-[16px] leading-[1.55] text-ink-700 mt-2">
                <span className={`font-sans text-[10px] uppercase tracking-[0.18em] ${accentText} mr-1.5`}>
                  {kicker}
                </span>
                <span className={phraseText}>{phrases.join(', ')}</span>
              </p>
              <span className="font-mono text-[11px] text-ink-500 tabular-nums mt-1.5 inline-block">
                {a.total} mentions · net {tone === 'rust' ? '−' : '+'}
                {pct}
              </span>
            </div>
          </li>
        )
      })}
    </ol>
  )
}

function Recommendations({ items }) {
  if (!items?.length) return null
  return (
    <ol className="space-y-6 max-w-[68ch]">
      {items.map((rX, i) => (
        <li key={`rec-${i}`} className="grid grid-cols-[56px_1fr] sm:grid-cols-[64px_1fr] gap-4 items-baseline">
          <span className="font-serif text-[40px] sm:text-[44px] leading-none text-accent-600 tabular-nums">
            {String(i + 1).padStart(2, '0')}
          </span>
          <p className="font-serif text-[19px] leading-[1.5] text-ink-900">{rX}</p>
        </li>
      ))}
    </ol>
  )
}

function HeroSkeleton() {
  return (
    <div className="border-t border-b border-ink-900 bg-cream-50">
      <div className="mx-auto max-w-[1240px] px-6 lg:px-10 py-14 grid lg:grid-cols-[1.4fr_1fr] gap-10">
        <div className="space-y-6">
          <div className="ed-skeleton h-5 w-32" />
          <div className="ed-skeleton h-[72px] w-[58%]" />
          <div className="ed-skeleton h-6 w-[78%]" />
        </div>
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="ed-skeleton h-10" />
          ))}
        </div>
      </div>
    </div>
  )
}

function ErrorState({ message }) {
  return (
    <div className="mx-auto max-w-[640px] px-6 py-24 text-center">
      <AlertTriangle size={28} className="mx-auto text-rust-600" />
      <h2 className="font-serif text-[32px] text-ink-900 mt-4">We couldn&rsquo;t load this analysis.</h2>
      <p className="font-serif italic text-[17px] text-ink-600 mt-2">{message || 'Try refreshing the page.'}</p>
    </div>
  )
}

function fmtDuration(ms) {
  if (ms == null) return '—'
  if (ms < 1000) return `${ms} ms`
  const s = ms / 1000
  if (s < 60) return `${s.toFixed(1)} s`
  return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`
}

function fmtLang(metrics) {
  if (!metrics) return '—'
  if (metrics.language_mix) {
    return Object.entries(metrics.language_mix)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([k, v]) => `${k.toUpperCase()} ${Math.round(v)}%`)
      .join(' · ')
  }
  const primary = metrics.primary_language
  return primary ? String(primary).toUpperCase() : '—'
}

function SectionLabel({ kicker, title, dek }) {
  return (
    <header className="max-w-[68ch]">
      <div className="font-mono text-xs tracking-[0.06em] text-accent-600">{kicker}</div>
      <h2 className="font-serif text-[32px] sm:text-[40px] leading-[1.05] tracking-[-0.015em] text-ink-900 mt-2">
        {title}
      </h2>
      {dek && <p className="font-serif italic text-[17px] leading-snug text-ink-600 mt-2">{dek}</p>}
    </header>
  )
}

function splitConclusion(summaryText) {
  if (!summaryText) return { main: '', conclusion: '' }
  const idx = summaryText.indexOf('CONCLUSION')
  if (idx === -1) return { main: summaryText, conclusion: '' }
  let head = summaryText.slice(0, idx).replace(/\s+$/g, '')
  if (head.endsWith('=')) {
    const lastNl = head.lastIndexOf('\n')
    if (lastNl !== -1) head = head.slice(0, lastNl).replace(/\s+$/g, '')
  }
  let rest = summaryText.slice(idx + 'CONCLUSION'.length)
  if (rest.startsWith('\n')) rest = rest.slice(1)
  if (rest.startsWith('=')) {
    const nl = rest.indexOf('\n')
    if (nl !== -1) rest = rest.slice(nl + 1)
  }
  return { main: head.trim(), conclusion: rest.trim() }
}

function takeawayLines(summaryText, max = 3) {
  const { main, conclusion } = splitConclusion(summaryText || '')
  const blob = conclusion || main || ''
  if (!blob.trim()) return []
  return blob
    .split(/\n+/)
    .map((s) => s.trim())
    .filter(Boolean)
    .slice(0, max)
}

export default function AnalysisDetail() {
  const { id } = useParams()
  const [analysis, setAnalysis] = useState(null)
  const [result, setResult] = useState(null)
  const [project, setProject] = useState(null)
  const [error, setError] = useState('')

  const fetchOnce = async () => {
    try {
      const { data } = await api.get(`/analyses/${id}`)
      setAnalysis(data?.analysis || null)
      setResult(data?.result || null)
      setError('')
      return data?.analysis?.status
    } catch (e) {
      console.error(e)
      const detail = e?.response?.data?.detail
      const msg = (typeof detail === 'string' && detail) || e?.message || 'Could not load this analysis.'
      setError(msg)
      return null
    }
  }

  useEffect(() => {
    setAnalysis(null)
    setResult(null)
    setError('')
    fetchOnce()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  useEffect(() => {
    const status = analysis?.status
    if (status !== 'processing' && status !== 'pending') return undefined
    const t = setInterval(() => {
      fetchOnce()
    }, 4000)
    return () => clearInterval(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analysis?.status, id])

  useEffect(() => {
    const pid = analysis?.project_id
    if (!pid) return undefined
    let cancel = false
    api
      .get(`/projects/${pid}`)
      .then(({ data }) => {
        if (!cancel) setProject(data)
      })
      .catch(() => {})
    return () => {
      cancel = true
    }
  }, [analysis?.project_id])

  const verdict = useMemo(() => verdictFor(result?.sentiment_summary), [result])

  const exportFile = async (fmt) => {
    const res = await api.get(`/analyses/${id}/export/${fmt}`, { responseType: 'blob' })
    const url = URL.createObjectURL(res.data)
    const a2 = document.createElement('a')
    a2.href = url
    a2.download = `reviewscope_${id}.${fmt}`
    a2.click()
    URL.revokeObjectURL(url)
  }

  const startRun = async () => {
    await api.post(`/analyses/${id}/run`, {})
    fetchOnce()
  }

  if (error && !analysis) return <ErrorState message={error} />
  if (!analysis) {
    return (
      <article className="bg-paper-50 text-ink-900 min-h-[50vh]">
        <HeroSkeleton />
      </article>
    )
  }

  const a = analysis
  const r = result || {}
  const completed = a.status === 'completed' && !!r.sentiment_summary
  const pending = a.status === 'pending'
  const processing = a.status === 'processing'
  const failed = a.status === 'failed'

  const insightPulls =
    Array.isArray(r.insights) && r.insights.length
      ? r.insights.slice(0, 3)
      : takeawayLines(r.summary_text, 3)

  const showKeywords =
    !!(r.keywords?.positive_keywords?.length || r.keywords?.negative_keywords?.length || r.keywords?.neutral_keywords?.length)

  if (!completed) {
    return (
      <article className="bg-paper-50 text-ink-900 pb-24">
        <div className="border-b border-rule-200 bg-paper-50">
          <div className="mx-auto max-w-[1240px] px-6 lg:px-10 min-h-[48px] flex flex-wrap items-center justify-between gap-3 py-3">
            <Link
              to={`/projects/${a.project_id || ''}`}
              className="inline-flex items-center gap-2 font-sans text-xs text-ink-600 hover:text-ink-900 transition-colors focus-ring rounded-sm"
            >
              <ArrowLeft size={14} /> Back to project
            </Link>
            <MastheadBreadcrumb
              projectName={project?.name || `Project #${a.project_id}`}
              projectId={a.project_id}
              fileName={a.file_name}
            />
          </div>
        </div>

        <div className="mx-auto max-w-[1240px] px-6 lg:px-10 py-10 space-y-6">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <div className="font-mono text-xs text-accent-600 tracking-[0.06em]">Analysis</div>
              <h1 className="font-serif text-[32px] sm:text-[40px] mt-2 text-ink-900 truncate max-w-xl">{a.file_name}</h1>
              <div className="flex flex-wrap gap-3 mt-3 items-center font-sans text-sm text-ink-500">
                <StatusPill status={a.status} />
              </div>
            </div>
          </div>

          {pending && (
            <div className="rounded-[8px] bg-cream-50 border border-rule-300 p-8 text-center max-w-xl">
              <Play className="mx-auto mb-4 text-accent-600" size={28} />
              <h2 className="font-serif text-2xl text-ink-900">Ready to analyze</h2>
              <p className="font-serif italic text-ink-600 mt-2 text-sm mb-6">
                The dataset is uploaded. Start the NLP pipeline when you are ready.
              </p>
              <button type="button" onClick={() => startRun()} className="btn-primary px-6">
                <Play size={14} /> Start analysis
              </button>
            </div>
          )}

          {(processing || failed) && <ProcessingView analysis={a} />}
          {(failed || processing) && !pending && (
            <button type="button" onClick={() => startRun()} className="btn-secondary">
              <Play size={14} /> Retry run
            </button>
          )}

          {error && (
            <p className="text-sm text-rust-600 border border-rule-300 rounded-[4px] px-3 py-2 bg-rust-50">{error}</p>
          )}
        </div>
      </article>
    )
  }

  return (
    <article className="bg-paper-50 text-ink-900 pb-32">
      <div className="border-b border-rule-200 bg-paper-50">
        <div className="mx-auto max-w-[1240px] px-6 lg:px-10 min-h-[48px] flex flex-wrap items-center justify-between gap-3 py-3">
          <Link
            to={`/projects/${a.project_id || ''}`}
            className="inline-flex items-center gap-2 font-sans text-[12px] text-ink-600 hover:text-ink-900 transition-colors focus-ring rounded-sm"
          >
            <ArrowLeft size={14} /> Back to project
          </Link>
          <MastheadBreadcrumb
            projectName={project?.name || `Project #${a.project_id}`}
            projectId={a.project_id}
            fileName={a.file_name}
          />
          <div className="flex items-center gap-1.5 w-full sm:w-auto justify-end">
            <button type="button" className="btn-ghost" onClick={() => exportFile('csv')}>
              <FileSpreadsheet size={14} /> CSV
            </button>
            <button type="button" className="btn-primary" onClick={() => exportFile('pdf')}>
              <Download size={14} /> PDF
            </button>
          </div>
        </div>
      </div>

      <VerdictMasthead
        verdict={verdict}
        sentiment={r.sentiment_summary}
        total={a.total_reviews ?? r.metrics?.total_reviews ?? r.sentiment_summary?.total}
        duration={fmtDuration(a.duration_ms)}
        language={fmtLang(r.metrics)}
      />

      {(() => {
        const narrative = parseConclusion(r.summary_text)
        if (narrative) {
          return (
            <section className="mx-auto max-w-[1240px] px-6 lg:px-10 py-16">
              <SectionLabel
                kicker="01"
                title="The brief"
                dek="What customers are actually saying — strengths, problems, and what to do about them."
              />
              <div className="mt-10">
                <NarrativeBrief data={narrative} verdictTone={verdict.tone} />
              </div>
            </section>
          )
        }
        if (insightPulls.length === 0) return null
        return (
          <section className="mx-auto max-w-[1240px] px-6 lg:px-10 py-16">
            <SectionLabel kicker="01" title="The brief" dek="Key takeaways before you scroll." />
            <div className="grid md:grid-cols-3 gap-x-10 gap-y-6 mt-10">
              {insightPulls.map((s, i) => (
                <PullQuote
                  key={i}
                  tone={i === 0 ? verdict.tone : 'rule'}
                  kicker={`Point ${String(i + 1).padStart(2, '0')}`}
                >
                  {s}
                </PullQuote>
              ))}
            </div>
            {(() => {
              const wrong = pickAspectStories(r.aspects, 'bad', 4)
              const good = pickAspectStories(r.aspects, 'good', 4)
              if (!wrong.length && !good.length) return null
              return (
                <div className="grid lg:grid-cols-2 gap-x-12 gap-y-10 mt-12 border-t border-rule-200 pt-12">
                  {wrong.length > 0 && (
                    <div>
                      <h3 className="font-sans text-[10px] uppercase tracking-[0.2em] text-rust-700 mb-4">
                        What&rsquo;s not working
                      </h3>
                      <AspectStoryList items={wrong} tone="rust" />
                    </div>
                  )}
                  {good.length > 0 && (
                    <div>
                      <h3 className="font-sans text-[10px] uppercase tracking-[0.2em] text-moss-700 mb-4">
                        What&rsquo;s working
                      </h3>
                      <AspectStoryList items={good} tone="moss" />
                    </div>
                  )}
                </div>
              )
            })()}
            {!!(r.recommendations && r.recommendations.length) && (
              <div className="mt-12 border-t border-rule-200 pt-12">
                <h3 className="font-sans text-[10px] uppercase tracking-[0.2em] text-accent-600 mb-4">
                  What to do next
                </h3>
                <Recommendations items={r.recommendations} />
              </div>
            )}
          </section>
        )
      })()}

      {!!(r.sample_reviews && r.sample_reviews.length) && (
        <section className="border-t border-rule-200 bg-cream-50/60">
          <div className="mx-auto max-w-[1240px] px-6 lg:px-10 py-16">
            <SectionLabel
              kicker="02"
              title="Voices, in their own words"
              dek="Representative excerpts with detected aspects."
            />
            <div className="mt-10">
              <SampleCards samples={r.sample_reviews || []} />
            </div>
          </div>
        </section>
      )}

      <section className="mx-auto max-w-[1240px] px-6 lg:px-10 py-16">
        <SectionLabel
          kicker="03"
          title="Top aspects, ranked"
          dek="The full aspect breakdown by net sentiment."
        />
        <div className="mt-10">
          <AspectAnnotatedChart aspects={r.aspects} />
        </div>
      </section>

      <section className="border-t border-rule-200 bg-cream-50/60">
        <div className="mx-auto max-w-[1240px] px-6 lg:px-10 py-16">
          <SectionLabel
            kicker="04"
            title="Sentiment, in one figure"
            dek="Distribution of positive, neutral and negative reviews."
          />
          <div className="mt-10">
            <SentimentDonut sentiment={r.sentiment_summary} />
          </div>
        </div>
      </section>

      {showKeywords && (
        <section className="mx-auto max-w-[1240px] px-6 lg:px-10 py-16">
          <SectionLabel
            kicker="05"
            title="Three rooms, three conversations"
            dek="Phrases that distinguish star buckets."
          />
          <div className="mt-10">
            <KeywordBands keywords={r.keywords} />
          </div>
        </section>
      )}

      <section className="border-t border-rule-200 bg-cream-50/60">
        <div className="mx-auto max-w-[1240px] px-6 lg:px-10 py-16">
          <SectionLabel kicker="06" title="Themes the model surfaced" dek="BERTopic clusters." />
          <div className="mt-10">
            <TopicsDek topics={r.topics} />
          </div>
        </div>
      </section>

      <footer className="mx-auto max-w-[1240px] px-6 lg:px-10 pt-10">
        <div className="border-t border-rule-300 pt-6 flex flex-wrap items-center justify-between gap-4 font-sans text-[11px] uppercase tracking-[0.18em] text-ink-500">
          <span>ReviewScope · Analysis #{id}</span>
          <span className="font-mono normal-case tracking-normal">{new Date(a.created_at || Date.now()).toLocaleString()}</span>
        </div>
      </footer>
    </article>
  )
}
