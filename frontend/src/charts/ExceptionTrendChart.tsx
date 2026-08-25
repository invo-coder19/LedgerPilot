import React from 'react'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend,
} from 'recharts'
import type { ExceptionTrendPoint } from '../types'

interface ExceptionTrendChartProps {
  data: ExceptionTrendPoint[]
}

const ExceptionTrendChart: React.FC<ExceptionTrendChartProps> = ({ data }) => (
  <ResponsiveContainer width="100%" height={220}>
    <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
      <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
      <XAxis
        dataKey="date"
        tick={{ fill: '#64748b', fontSize: 10 }}
        tickFormatter={(v) => v.slice(5)}
        axisLine={false}
        tickLine={false}
      />
      <YAxis
        tick={{ fill: '#64748b', fontSize: 10 }}
        axisLine={false}
        tickLine={false}
        width={30}
      />
      <Tooltip
        contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }}
        labelStyle={{ color: '#94a3b8' }}
        itemStyle={{ color: '#e2e8f0' }}
      />
      <Legend
        formatter={(v) => <span style={{ color: '#94a3b8', fontSize: 11 }}>{v.charAt(0).toUpperCase() + v.slice(1)}</span>}
      />
      <Bar dataKey="open" name="Open" fill="#ef4444" radius={[3, 3, 0, 0]} />
      <Bar dataKey="resolved" name="Resolved" fill="#22c55e" radius={[3, 3, 0, 0]} />
    </BarChart>
  </ResponsiveContainer>
)

export default ExceptionTrendChart
