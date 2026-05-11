

const LABELS = {
  pending: 'Pending',
  processing: 'Processing',
  completed: 'Completed',
  failed: 'Failed',
}

const STYLE = {
  pending: 'bg-cream-50 text-ink-700 shadow-[inset_0_0_0_1px_var(--rule-300)]',
  processing:
    'bg-ochre-50 text-ochre-700 shadow-[inset_0_0_0_1px_var(--ochre-700)] [&>span:first-child]:animate-pulse-dot',
  completed: 'bg-moss-50 text-moss-700 shadow-[inset_0_0_0_1px_var(--moss-600)]',
  failed: 'bg-rust-50 text-rust-700 shadow-[inset_0_0_0_1px_var(--rust-600)]',
}

export default function StatusPill({ status = 'pending', className = '' }) {
  const key = LABELS[status] ? status : 'pending'
  return (
    <span
      className={`inline-flex items-center gap-1.5 h-5 px-2 rounded-[2px] font-sans text-[11px] font-medium uppercase tracking-[0.08em] ${STYLE[key]} ${className}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current" aria-hidden />
      {LABELS[key]}
    </span>
  )
}
