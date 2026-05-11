import { Layers, Inbox } from 'lucide-react';

export default function TopicsDisplay({ data }) {
  const topics = data?.topics || [];

  if (!topics.length) {
    return (
      <div className="rs-card p-8 flex flex-col items-center justify-center text-center gap-2">
        <span className="grid place-items-center h-10 w-10 rounded-[12px]"
          style={{ background: 'hsl(var(--rs-bg-muted))', color: 'hsl(var(--rs-fg-muted))' }}>
          <Inbox size={18} />
        </span>
        <div className="text-sm font-medium" style={{ color: 'hsl(var(--rs-fg))' }}>No topics discovered</div>
        <div className="text-xs" style={{ color: 'hsl(var(--rs-fg-muted))' }}>
          The dataset was too small or homogeneous for topic modeling.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {topics.map((t, idx) => (
        <div key={t.topic_id ?? idx} className="rs-card p-4 rs-card-hover">
          <div className="flex items-center gap-3 mb-2.5">
            <span className="grid place-items-center h-7 w-7 rounded-[8px] text-xs font-semibold tabular-nums"
              style={{ background: 'hsl(var(--rs-accent) / 0.12)', color: 'hsl(var(--rs-accent))' }}>
              {idx + 1}
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <Layers size={14} style={{ color: 'hsl(var(--rs-fg-muted))' }} />
                <span className="text-sm font-medium" style={{ color: 'hsl(var(--rs-fg))' }}>
                  Topic {t.topic_id ?? idx}
                </span>
              </div>
            </div>
            <span className="text-xs tabular-nums" style={{ color: 'hsl(var(--rs-fg-muted))' }}>
              {t.count} reviews
            </span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {(t.keywords || []).slice(0, 8).map((k, i) => (
              <span key={`${k}-${i}`} className="text-xs px-2 py-0.5 rounded-full"
                style={{ background: 'hsl(var(--rs-surface-2))', border: '1px solid hsl(var(--rs-border))', color: 'hsl(var(--rs-fg))' }}>
                {k}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
