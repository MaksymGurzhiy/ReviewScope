import { createElement } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

const ACCENT = {
  positive: 'hsl(152 64% 42%)',
  neutral:  'hsl(38 92% 50%)',
  negative: 'hsl(350 78% 55%)',
};

function pct(part, total) {
  if (!total) return 0;
  return Math.round((part / total) * 100);
}

function round1(v) {
  if (v == null || isNaN(v)) return 0;
  return Math.round(Number(v) * 10) / 10;
}

function StatRow({ tone, label, value, percent, Icon }) {
  return (
    <div className="flex items-center gap-3 py-2">
      <span className="grid place-items-center h-8 w-8 rounded-[10px]"
        style={{ background: `hsl(var(--rs-${tone}-soft))`, color: `hsl(var(--rs-${tone}))` }}>
        {createElement(Icon, { size: 14 })}
      </span>
      <div className="flex-1">
        <div className="text-sm font-medium" style={{ color: 'hsl(var(--rs-fg))' }}>{label}</div>
        <div className="text-xs" style={{ color: 'hsl(var(--rs-fg-muted))' }}>{value} reviews</div>
      </div>
      <div className="text-sm tabular-nums font-semibold" style={{ color: `hsl(var(--rs-${tone}))` }}>
        {percent}%
      </div>
    </div>
  );
}

export default function SentimentChart({ data }) {
  if (!data) return null;
  const total = data.total ?? ((data.positive || 0) + (data.neutral || 0) + (data.negative || 0));
  const pos = data.positive || 0;
  const neu = data.neutral || 0;
  const neg = data.negative || 0;

  const posPct = round1(data.positive_percent ?? pct(pos, total));
  const neuPct = round1(data.neutral_percent  ?? pct(neu, total));
  const negPct = round1(data.negative_percent ?? pct(neg, total));

  const chartData = [
    { name: 'Positive', value: pos, fill: ACCENT.positive, key: 'pos' },
    { name: 'Neutral',  value: neu, fill: ACCENT.neutral,  key: 'neu' },
    { name: 'Negative', value: neg, fill: ACCENT.negative, key: 'neg' },
  ];

  return (
    <div className="grid lg:grid-cols-[280px_1fr] gap-6 items-center">
      <div className="relative h-[240px]">
        <ResponsiveContainer>
          <PieChart>
            <Pie data={chartData} dataKey="value" innerRadius={70} outerRadius={104}
              paddingAngle={2} stroke="hsl(var(--rs-surface))" strokeWidth={3}>
              {chartData.map((d) => <Cell key={d.key} fill={d.fill} />)}
            </Pie>
            <Tooltip contentStyle={{ background: 'hsl(var(--rs-surface))', border: '1px solid hsl(var(--rs-border-strong))', borderRadius: 8, fontSize: 12 }} />
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 grid place-items-center pointer-events-none">
          <div className="text-center">
            <div className="rs-display !text-[34px]">{posPct}%</div>
            <div className="text-xs mt-1" style={{ color: 'hsl(var(--rs-fg-muted))' }}>positive</div>
          </div>
        </div>
      </div>

      <div>
        <div className="space-y-1">
          <StatRow tone="pos" label="Positive" value={pos} percent={posPct} Icon={TrendingUp} />
          <StatRow tone="neu" label="Neutral"  value={neu} percent={neuPct} Icon={Minus} />
          <StatRow tone="neg" label="Negative" value={neg} percent={negPct} Icon={TrendingDown} />
        </div>

        <div className="mt-5">
          <div className="flex justify-between text-xs mb-2" style={{ color: 'hsl(var(--rs-fg-muted))' }}>
            <span>Distribution</span>
            <span className="tabular-nums">{total} total</span>
          </div>
          <div className="flex h-2 w-full overflow-hidden rounded-full" style={{ background: 'hsl(var(--rs-bg-muted))' }}>
            <div style={{ width: `${posPct}%`, background: ACCENT.positive }} />
            <div style={{ width: `${neuPct}%`, background: ACCENT.neutral }} />
            <div style={{ width: `${negPct}%`, background: ACCENT.negative }} />
          </div>
        </div>
      </div>
    </div>
  );
}
