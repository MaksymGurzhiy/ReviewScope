import { Lightbulb, Target } from 'lucide-react';

export default function InsightsPanel({ insights = [], recommendations = [] }) {
  return (
    <div className="grid md:grid-cols-2 gap-4">
      <div className="rs-card p-5">
        <div className="flex items-center gap-2 mb-4">
          <span className="grid place-items-center h-8 w-8 rounded-[10px]"
            style={{ background: 'hsl(var(--rs-neu-soft))', color: 'hsl(var(--rs-neu))' }}>
            <Lightbulb size={15} />
          </span>
          <h3 className="rs-h2">Key insights</h3>
        </div>
        {insights.length === 0 ? (
          <p className="text-sm" style={{ color: 'hsl(var(--rs-fg-muted))' }}>No insights yet.</p>
        ) : (
          <ul className="space-y-2.5">
            {insights.map((s, i) => (
              <li key={i} className="flex gap-3 text-sm leading-relaxed" style={{ color: 'hsl(var(--rs-fg))' }}>
                <span className="mt-2 h-1.5 w-1.5 rounded-full flex-shrink-0" style={{ background: 'hsl(var(--rs-accent))' }} />
                <span>{s}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="rs-card p-5">
        <div className="flex items-center gap-2 mb-4">
          <span className="grid place-items-center h-8 w-8 rounded-[10px]"
            style={{ background: 'hsl(var(--rs-pos-soft))', color: 'hsl(var(--rs-pos))' }}>
            <Target size={15} />
          </span>
          <h3 className="rs-h2">Recommendations</h3>
        </div>
        {recommendations.length === 0 ? (
          <p className="text-sm" style={{ color: 'hsl(var(--rs-fg-muted))' }}>No recommendations yet.</p>
        ) : (
          <ol className="space-y-2.5">
            {recommendations.map((s, i) => (
              <li key={i} className="flex gap-3 text-sm leading-relaxed" style={{ color: 'hsl(var(--rs-fg))' }}>
                <span className="grid place-items-center flex-shrink-0 h-5 w-5 rounded-full text-[11px] font-semibold tabular-nums"
                  style={{ background: 'hsl(var(--rs-accent) / 0.12)', color: 'hsl(var(--rs-accent))' }}>
                  {i + 1}
                </span>
                <span>{s}</span>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}
