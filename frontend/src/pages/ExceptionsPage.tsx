import React, { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import StatusBadge from '../components/StatusBadge'
import SeverityBadge from '../components/SeverityBadge'
import Pagination from '../components/Pagination'
import LoadingSkeleton from '../components/LoadingSkeleton'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import { exceptionService, type ExceptionFilters } from '../services/exceptionService'
import type { FinancialException, ExceptionStatus, ExceptionSeverity, PaginatedResponse } from '../types'
import { formatCurrency, formatDateTime } from '../utils/format'

const QUICK_FILTERS: Array<{ label: string; filter: Partial<ExceptionFilters> }> = [
  { label: 'All', filter: {} },
  { label: 'Open', filter: { status: 'OPEN' } },
  { label: 'In Review', filter: { status: 'IN_REVIEW' } },
  { label: 'Resolved', filter: { status: 'RESOLVED' } },
  { label: 'High', filter: { severity: 'HIGH' } },
  { label: 'Critical', filter: { severity: 'CRITICAL' } },
]

const ExceptionsPage: React.FC = () => {
  const navigate = useNavigate()
  const [data, setData] = useState<PaginatedResponse<FinancialException> | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [filters, setFilters] = useState<ExceptionFilters>({ page: 1, page_size: 20 })
  const [activeQuick, setActiveQuick] = useState(0)

  const load = useCallback(async () => {
    setIsLoading(true)
    setError('')
    try {
      const result = await exceptionService.list(filters)
      setData(result)
    } catch { setError('Failed to load exceptions.') }
    finally { setIsLoading(false) }
  }, [filters])

  useEffect(() => { load() }, [load])

  const applyQuick = (idx: number) => {
    setActiveQuick(idx)
    setFilters({ page: 1, page_size: 20, ...QUICK_FILTERS[idx].filter })
  }

  return (
    <div className="p-6 space-y-4 animate-fade-in">
      <div>
        <h1 className="text-xl font-bold text-slate-100">Exceptions</h1>
        <p className="text-sm text-slate-400 mt-0.5">Financial discrepancies requiring attention</p>
      </div>

      {/* Quick filters */}
      <div className="flex flex-wrap gap-2">
        {QUICK_FILTERS.map((qf, idx) => (
          <button
            key={qf.label}
            id={`exception-filter-${qf.label.toLowerCase().replace(/\s/g, '-')}`}
            onClick={() => applyQuick(idx)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
              activeQuick === idx
                ? 'bg-brand-500 border-brand-500 text-white'
                : 'border-surface-border text-slate-400 hover:bg-surface-hover hover:text-slate-200'
            }`}
          >
            {qf.label}
          </button>
        ))}
      </div>

      <div className="card">
        {error ? <ErrorState message={error} onRetry={load} />
          : isLoading ? <LoadingSkeleton rows={8} cols={7} />
          : !data || data.items.length === 0 ? (
            <EmptyState
              title="No exceptions found"
              description="There are currently no exceptions matching your selected filters."
            />
          ) : (
            <>
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Source</th>
                      <th>Type</th>
                      <th>Amount</th>
                      <th>Severity</th>
                      <th>Status</th>
                      <th>Created</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((exc) => (
                      <tr key={exc.id} onClick={() => navigate(`/exceptions/${exc.id}`)}>
                        <td className="font-mono text-xs text-slate-400">{exc.source_id}</td>
                        <td className="text-slate-300 text-xs">{exc.exception_type.replace(/_/g, ' ')}</td>
                        <td className="text-money">{formatCurrency(exc.amount)}</td>
                        <td><SeverityBadge severity={exc.severity} /></td>
                        <td><StatusBadge status={exc.status} /></td>
                        <td className="text-slate-400 text-xs">{formatDateTime(exc.created_at)}</td>
                        <td>
                          <span className="text-brand-400 text-xs hover:text-brand-300">View →</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Pagination page={data.page} pages={data.pages} total={data.total}
                page_size={data.page_size}
                onPageChange={(p) => setFilters(f => ({ ...f, page: p }))} />
            </>
          )}
      </div>
    </div>
  )
}

export default ExceptionsPage
