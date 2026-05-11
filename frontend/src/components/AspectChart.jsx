import { BarChart, Bar, XAxis, YAxis, ReferenceLine, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const POS = 'hsl(152 64% 42%)';
const NEG = 'hsl(350 78% 55%)';

export default function AspectChart({ data }) {
  const aspects = data?.aspects || [];
  if (!aspects.length) {
    return <div className="py-12 text-center text-sm" style={{ color: 'hsl(var(--rs-fg-muted))' }}>No aspects extracted.</div>;
  }

  const chartData = aspects.slice(0, 10).map((a) => {
    const total = a.total_mentions || (a.positive + a.negative + a.neutral) || 1;
    const score = ((a.positive - a.negative) / total) * 100;
    return { aspect: a.aspect, score: Math.round(score), mentions: total };
  }).sort((a, b) => b.score - a.score);

  const polarityTone = (p) => p === 'positive' ? 'pos' : p === 'negative' ? 'neg' : 'neu';

  return (
    <div className="grid lg:grid-cols-[1fr_360px] gap-6">
      <div className="h-[340px]">
        <ResponsiveContainer>
          <BarChart data={chartData} layout="vertical" margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
            <XAxis type="number" domain={[-100, 100]} tick={{ fontSize: 11, fill: 'hsl(var(--rs-fg-muted))' }} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="aspect" width={110} tick={{ fontSize: 12, fill: 'hsl(var(--rs-fg))' }} axisLine={false} tickLine={false} />
            <ReferenceLine x={0} stroke="hsl(var(--rs-border-strong))" />
            <Tooltip cursor={{ fill: 'hsl(var(--rs-bg-muted))' }}
              contentStyle={{ background: 'hsl(var(--rs-surface))', border: '1px solid hsl(var(--rs-border-strong))', borderRadius: 8, fontSize: 12 }}
              formatter={(v, _n, p) => [`${v} (net)`, p.payload.aspect]} labelFormatter={() => ''} />
            <Bar dataKey="score" radius={[6, 6, 6, 6]} barSize={18}>
              {chartData.map((d, i) => <Cell key={i} fill={d.score >= 0 ? POS : NEG} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-2 gap-2 content-start">
        {aspects.slice(0, 8).map((a) => {
          const tone = polarityTone(a.polarity);
          return (
            <div key={a.aspect} className="rs-card p-3 flex flex-col gap-1.5 rs-card-hover">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium truncate" style={{ color: 'hsl(var(--rs-fg))' }}>{a.aspect}</span>
                <span className={`rs-tone-${tone} text-[11px] px-1.5 py-0.5 rounded-full font-medium capitalize`}>
                  {a.polarity || 'neutral'}
                </span>
              </div>
              <div className="text-xs tabular-nums" style={{ color: 'hsl(var(--rs-fg-muted))' }}>
                {a.total_mentions} mentions
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
