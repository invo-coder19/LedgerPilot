import React from 'react'
import { formatCompact } from '../utils/format'

interface KPICardProps {
  title: string
  value: number | string
  subtitle?: string
  icon: React.ReactNode
  trend?: 'up' | 'down' | 'neutral'
  trendValue?: string
  isCurrency?: boolean
  colorClass?: string
}

const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  trendValue,
  isCurrency = false,
  colorClass = 'text-brand-400',
}) => {
  const displayValue = isCurrency && typeof value === 'number'
    ? formatCompact(value)
    : value

  return (
    <div className="card p-5 flex flex-col gap-4 hover:shadow-card-hover transition-shadow duration-200 animate-fade-in">
      <div className="flex items-start justify-between">
        <div className={`p-2 rounded-lg bg-surface ${colorClass}`}>
          {icon}
        </div>
        {trend && trendValue && (
          <span
            className={`text-xs font-medium px-2 py-0.5 rounded-full ${
              trend === 'up'
                ? 'text-green-400 bg-green-400/10'
                : trend === 'down'
                ? 'text-red-400 bg-red-400/10'
                : 'text-slate-400 bg-slate-400/10'
            }`}
          >
            {trendValue}
          </span>
        )}
      </div>
      <div>
        <p className="text-2xl font-semibold text-slate-100 font-mono tabular-nums">
          {displayValue}
        </p>
        <p className="text-sm text-slate-400 mt-0.5">{title}</p>
        {subtitle && <p className="text-xs text-slate-500 mt-1">{subtitle}</p>}
      </div>
    </div>
  )
}

export default KPICard
