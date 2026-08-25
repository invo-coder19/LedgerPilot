import React, { useEffect, useState, useCallback } from 'react'
import StatusBadge from '../components/StatusBadge'
import Pagination from '../components/Pagination'
import LoadingSkeleton from '../components/LoadingSkeleton'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import { settlementService } from '../services/settlementService'
import type { Settlement, SettlementStatus, PaginatedResponse } from '../types'
import { formatCurrency, formatDate } from '../utils/format'

const STATUSES: SettlementStatus[] = ['PENDING', 'PROCESSED', 'FAILED']

const SettlementsPage: React.FC = () => {
  const [data, setData] = useState<PaginatedResponse<Settlement> | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [statusFilter, setStatusFilter] = useState<SettlementStatus | ''>('')
  const [page, setPage] = useState(1)

  const load = useCallback(async () => {
    setIsLoading(true)
    setError('')
    try {
      const result = await settlementService.list({ status: statusFilter || undefined, page, page_size: 20 })
      setData(result)
    } catch { setError('Failed to load settlements.') }
    finally { setIsLoading(false) }
  }, [statusFilter, page])

  useEffect(() => { load() }, [load])

  return (
    <div className="p-6 space-y-4 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Settlements</h1>
          <p className="text-sm text-slate-400 mt-0.5">Payment gateway settlement records</p>
        </div>
        <select id="settlement-status-filter" className="input w-44"
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value as SettlementStatus | ''); setPage(1) }}>
          <option value="">All Statuses</option>
          {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      <div className="card">
        {error ? <ErrorState message={error} onRetry={load} />
          : isLoading ? <LoadingSkeleton rows={8} cols={6} />
          : !data || data.items.length === 0 ? (
            <EmptyState title="No settlements found" description="No settlements match your current filters." />
          ) : (
            <>
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Settlement ID</th>
                      <th>Payment ID</th>
                      <th>Amount</th>
                      <th>Fee</th>
                      <th>Status</th>
                      <th>Settlement Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((s) => (
                      <tr key={s.id}>
                        <td className="font-mono text-brand-400 text-xs">{s.settlement_id}</td>
                        <td className="font-mono text-xs text-slate-400">{s.payment_id}</td>
                        <td className="text-money">{formatCurrency(s.settlement_amount)}</td>
                        <td className="text-slate-400">{formatCurrency(s.fee)}</td>
                        <td><StatusBadge status={s.status} /></td>
                        <td className="text-slate-400">{formatDate(s.settlement_date)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Pagination page={data.page} pages={data.pages} total={data.total}
                page_size={data.page_size} onPageChange={setPage} />
            </>
          )}
      </div>
    </div>
  )
}

export default SettlementsPage
