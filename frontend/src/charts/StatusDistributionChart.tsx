import React from 'react'
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend } from 'recharts'
import type { StatusDistributionItem } from '../types'

const COLORS: Record<string, string> = {
  SUCCESS:        '#22c55e',
  FAILED:         '#ef4444',
  PENDING:        '#3b82f6',
  REFUNDED:       '#f59e0b',
  PARTIAL_REFUND: '#f97316',
}

interface StatusDistributionChartProps {
  data: StatusDistributionItem[]
}

const RADIAN = Math.PI / 180
const renderCustomizedLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }: any) => {
  if (percent < 0.05) return null
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5
  const x = cx + radius * Math.cos(-midAngle * RADIAN)
  const y = cy + radius * Math.sin(-midAngle * RADIAN)
  return (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize={11} fontWeight={600}>
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  )
}

const StatusDistributionChart: React.FC<StatusDistributionChartProps> = ({ data }) => (
  <ResponsiveContainer width="100%" height={220}>
    <PieChart>
      <Pie
        data={data}
        cx="50%"
        cy="50%"
        innerRadius={55}
        outerRadius={85}
        dataKey="count"
        nameKey="status"
        labelLine={false}
        label={renderCustomizedLabel}
      >
        {data.map((entry, index) => (
          <Cell
            key={`cell-${index}`}
            fill={COLORS[entry.status] || '#64748b'}
          />
        ))}
      </Pie>
      <Tooltip
        formatter={(value, name) => [value, (name as string).replace(/_/g, ' ')]}
        contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }}
        labelStyle={{ color: '#94a3b8' }}
        itemStyle={{ color: '#e2e8f0' }}
      />
      <Legend
        formatter={(value) => <span style={{ color: '#94a3b8', fontSize: 11 }}>{value.replace(/_/g, ' ')}</span>}
      />
    </PieChart>
  </ResponsiveContainer>
)

export default StatusDistributionChart
