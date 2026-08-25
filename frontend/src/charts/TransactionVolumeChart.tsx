import React from 'react'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts'
import type { TransactionVolumePoint } from '../types'
import { formatCompact } from '../utils/format'

interface TransactionVolumeChartProps {
  data: TransactionVolumePoint[]
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="card p-3 text-xs">
        <p className="text-slate-400 mb-1">{label}</p>
        <p className="text-slate-200">
          <span className="text-brand-400 font-medium">{payload[0]?.value}</span> transactions
        </p>
        <p className="text-slate-200">
          <span className="text-green-400 font-medium">{formatCompact(payload[1]?.value || 0)}</span> volume
        </p>
      </div>
    )
  }
  return null
}

const TransactionVolumeChart: React.FC<TransactionVolumeChartProps> = ({ data }) => (
  <ResponsiveContainer width="100%" height={220}>
    <AreaChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
      <defs>
        <linearGradient id="gradCount" x1="0" y1="0" x2="0" y2="1">
          <stop offset="5%" stopColor="#2563eb" stopOpacity={0.3} />
          <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
        </linearGradient>
        <linearGradient id="gradAmount" x1="0" y1="0" x2="0" y2="1">
          <stop offset="5%" stopColor="#22c55e" stopOpacity={0.2} />
          <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
        </linearGradient>
      </defs>
      <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
      <XAxis
        dataKey="date"
        tick={{ fill: '#64748b', fontSize: 10 }}
        tickFormatter={(v) => v.slice(5)} // show MM-DD
        axisLine={false}
        tickLine={false}
      />
      <YAxis
        tick={{ fill: '#64748b', fontSize: 10 }}
        axisLine={false}
        tickLine={false}
        width={35}
      />
      <Tooltip content={<CustomTooltip />} />
      <Area
        type="monotone"
        dataKey="count"
        stroke="#2563eb"
        strokeWidth={2}
        fill="url(#gradCount)"
        dot={false}
      />
    </AreaChart>
  </ResponsiveContainer>
)

export default TransactionVolumeChart
