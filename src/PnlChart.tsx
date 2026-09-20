import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export type Trading = {
  trading_date: string
  net_pnl: string
}

function money(value: string | number) {
  return `₹${Number(value).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export default function PnlChart({ trading }: { trading: Trading[] }) {
  if (!trading.length) return <div className="empty-state">Trading records will appear here.</div>

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={trading}>
        <defs>
          <linearGradient id="pnlFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#d87550" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#d87550" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis dataKey="trading_date" tickLine={false} axisLine={false} tick={{ fill: '#8d887f', fontSize: 11 }} />
        <YAxis tickLine={false} axisLine={false} tick={{ fill: '#8d887f', fontSize: 11 }} tickFormatter={(value) => `₹${value / 1000}k`} />
        <Tooltip formatter={(value) => money(value as string)} contentStyle={{ border: '1px solid #e6ded2', borderRadius: 8, boxShadow: '0 8px 24px #39332b18' }} />
        <Area type="monotone" dataKey="net_pnl" stroke="#c85f3b" strokeWidth={3} fill="url(#pnlFill)" />
      </AreaChart>
    </ResponsiveContainer>
  )
}
