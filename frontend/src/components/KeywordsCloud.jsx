import { Star, Hash } from 'lucide-react';

function Group({ title, accent, items }) {
  if (!items?.length) return null;
  const max = Math.max(...items.map(([, s]) => s || 0), 1);

  return (
    <div className="rs-card p-4">
      <div className="flex items-center gap-2 mb-3">
        <span className="grid place-items-center h-7 w-7 rounded-[8px]"
          style={{ background: `hsl(var(--rs-${accent}-soft))`, color: `hsl(var(--rs-${accent}))` }}>
          <Star size={13} />
        </span>
        <h3 className="rs-h2">{title}</h3>
      </div>

      <ul className="space-y-2">
        {items.slice(0, 8).map(([phrase, score], i) => {
          const w = Math.max(8, Math.round((score / max) * 100));
          return (
            <li key={`${phrase}-${i}`} className="flex items-center gap-3">
              <span className="text-sm flex-1 truncate" style={{ color: 'hsl(var(--rs-fg))' }}>{phrase}</span>
              <div className="h-1.5 rounded-full overflow-hidden" style={{ width: 96, background: 'hsl(var(--rs-bg-muted))' }}>
                <div className="h-full rounded-full" style={{ width: `${w}%`, background: `hsl(var(--rs-${accent}))` }} />
              </div>
              <span className="text-xs tabular-nums w-10 text-right" style={{ color: 'hsl(var(--rs-fg-muted))' }}>
                {typeof score === 'number' ? score.toFixed(2) : score}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default function KeywordsCloud({ data }) {
  if (!data) return null;
  const { positive_keywords = [], neutral_keywords = [], negative_keywords = [], most_mentioned = [] } = data;
  const hasNeutral = neutral_keywords && neutral_keywords.length > 0;
  const cols = hasNeutral ? 'md:grid-cols-3' : 'md:grid-cols-2';

  return (
    <div className="space-y-4">
      <div className={`grid ${cols} gap-3`}>
        <Group title="Strengths (4–5 stars)" accent="pos" items={positive_keywords} />
        {hasNeutral && (
          <Group title="Mixed (3 stars)" accent="neu" items={neutral_keywords} />
        )}
        <Group title="Pain points (1–2 stars)" accent="neg" items={negative_keywords} />
      </div>

      {most_mentioned.length > 0 && (
        <div className="rs-card p-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="grid place-items-center h-7 w-7 rounded-[8px]"
              style={{ background: 'hsl(var(--rs-accent) / 0.12)', color: 'hsl(var(--rs-accent))' }}>
              <Hash size={13} />
            </span>
            <h3 className="rs-h2">Most mentioned overall</h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {most_mentioned.slice(0, 24).map((p, i) => {
              const size = i < 4 ? 15 : i < 10 ? 14 : 13;
              return (
                <span key={`${p}-${i}`} className="inline-flex items-center px-2.5 py-1 rounded-full"
                  style={{ fontSize: size, background: 'hsl(var(--rs-surface-2))', border: '1px solid hsl(var(--rs-border))', color: 'hsl(var(--rs-fg))' }}>
                  {p}
                </span>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
