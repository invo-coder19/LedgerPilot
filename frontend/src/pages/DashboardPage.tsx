import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import KPICard from '../components/KPICard'
import StatusBadge from '../components/StatusBadge'
import SeverityBadge from '../components/SeverityBadge'
import { KPISkeletons } from '../components/LoadingSkeleton'
import ErrorState from '../components/ErrorState'
import TransactionVolumeChart from '../charts/TransactionVolumeChart'
import StatusDistributionChart from '../charts/StatusDistributionChart'
import ExceptionTrendChart from '../charts/ExceptionTrendChart'
import { dashboardService } from '../services/dashboardService'
import { exceptionService } from '../services/exceptionService'
import { auditService } from '../services/auditService'
import type {
  DashboardSummary, FinancialException, AuditLog,
  TransactionVolumePoint, StatusDistributionItem, ExceptionTrendPoint,
} from '../types'
import { formatCurrency, formatDateTime } from '../utils/format'

const DashboardPage: React.FC = () => {
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [recentExceptions, setRecentExceptions] = useState<FinancialException[]>([])
  const [recentActivity, setRecentActivity] = useState<AuditLog[]>([])
  const [volumeData, setVolumeData] = useState<TransactionVolumePoint[]>([])
  const [statusData, setStatusData] = useState<StatusDistributionItem[]>([])
  const [trendData, setTrendData] = useState<ExceptionTrendPoint[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  const load = async () => {
    setIsLoading(true)
    setError('')
    try {
      const [sum, exc, audit, vol, stat, trend] = await Promise.all([
        dashboardService.getSummary(),
        exceptionService.list({ page_size: 5 }),
        auditService.list({ page_size: 8 }),
        dashboardService.getTransactionVolume(),
        dashboardService.getStatusDistribution(),
        dashboardService.getExceptionTrend(),
      ])
      setSummary(sum)
      setRecentExceptions(exc.items)
      setRecentActivity(audit.items)
      setVolumeData(vol)
      setStatusData(stat)
      setTrendData(trend)
    } catch {
      setError('Failed to load dashboard data.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  if (error) return (
    <div className="p-6">
      <ErrorState message={error} onRetry={load} />
    </div>
  )

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-100">Dashboard</h1>
        <p className="text-sm text-slate-400 mt-0.5">Financial operations overview — Acme Commerce Pvt Ltd</p>
      </div>

      {/* KPI Cards */}
      {isLoading ? <KPISkeletons /> : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <KPICard
            title="Total Transactions"
            value={summary?.total_transactions ?? 0}
            icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" /></svg>}
          />
          <KPICard
            title="Matched Transactions"
            value={summary?.matched_transactions ?? 0}
            colorClass="text-green-400"
            icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
          />
          <KPICard
            title="Unmatched Transactions"
            value={summary?.unmatched_transactions ?? 0}
            colorClass="text-orange-400"
            icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>}
          />
          <KPICard
            title="Open Exceptions"
            value={summary?.open_exceptions ?? 0}
            colorClass="text-red-400"
            icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" /></svg>}
          />
          <KPICard
            title="Amount Processed"
            value={summary?.total_transaction_value ?? 0}
            isCurrency
            colorClass="text-brand-400"
            icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
          />
          <KPICard
            title="Amount Settled"
            value={summary?.total_settlement_value ?? 0}
            isCurrency
            colorClass="text-green-400"
            icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" /></svg>}
          />
        </div>
      )}

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card p-5 lg:col-span-2">
          <h2 className="text-sm font-semibold text-slate-200 mb-4">Transaction Volume (Last 30 days)</h2>
          {isLoading ? <div className="skeleton h-52 w-full rounded" /> : <TransactionVolumeChart data={volumeData} />}
        </div>
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-slate-200 mb-4">Status Distribution</h2>
          {isLoading ? <div className="skeleton h-52 w-full rounded" /> : <StatusDistributionChart data={statusData} />}
        </div>
      </div>

      {/* Exception trend */}
      <div className="card p-5">
        <h2 className="text-sm font-semibold text-slate-200 mb-4">Exception Trend</h2>
        {isLoading ? <div className="skeleton h-52 w-full rounded" /> : <ExceptionTrendChart data={trendData} />}
      </div>

      {/* Bottom panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Recent exceptions */}
        <div className="card">
          <div className="flex items-center justify-between px-5 py-4 border-b border-surface-border">
            <h2 className="text-sm font-semibold text-slate-200">Recent Exceptions</h2>
            <Link to="/exceptions" className="text-xs text-brand-400 hover:text-brand-300">View all →</Link>
          </div>
          <div className="divide-y divide-surface-border">
            {recentExceptions.length === 0 ? (
              <p className="px-5 py-4 text-sm text-slate-500">No exceptions found.</p>
            ) : recentExceptions.map((exc) => (
              <Link
                key={exc.id}
                to={`/exceptions/${exc.id}`}
                className="flex items-start justify-between px-5 py-3 hover:bg-surface-hover transition-colors"
              >
                <div className="flex-1 min-w-0 mr-3">
                  <p className="text-xs font-medium text-slate-300 truncate">{exc.exception_type.replace(/_/g, ' ')}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{formatCurrency(exc.amount)}</p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <SeverityBadge severity={exc.severity} />
                  <StatusBadge status={exc.status} />
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Recent activity */}
        <div className="card">
          <div className="flex items-center justify-between px-5 py-4 border-b border-surface-border">
            <h2 className="text-sm font-semibold text-slate-200">Recent Activity</h2>
            <Link to="/audit-log" className="text-xs text-brand-400 hover:text-brand-300">View all →</Link>
          </div>
          <div className="divide-y divide-surface-border">
            {recentActivity.length === 0 ? (
              <p className="px-5 py-4 text-sm text-slate-500">No activity yet.</p>
            ) : recentActivity.map((log) => (
              <div key={log.id} className="flex items-start gap-3 px-5 py-3">
                <div className="w-1.5 h-1.5 bg-brand-500 rounded-full mt-1.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-slate-300">{log.description}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{formatDateTime(log.created_at)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default DashboardPage
