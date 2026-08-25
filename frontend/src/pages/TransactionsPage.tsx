import React, { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import StatusBadge from '../components/StatusBadge'
import Pagination from '../components/Pagination'
import LoadingSkeleton from '../components/LoadingSkeleton'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import { transactionService, type TransactionFilters } from '../services/transactionService'
import type { Transaction, TransactionStatus, PaginatedResponse } from '../types'
import { formatCurrency, formatDateTime } from '../utils/format'

const STATUSES: TransactionStatus[] = ['SUCCESS', 'FAILED', 'REFUNDED', 'PARTIAL_REFUND', 'PENDING']

const TransactionsPage: React.FC = () => {
  const navigate = useNavigate()
  const [data, setData] = useState<PaginatedResponse<Transaction> | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [filters, setFilters] = useState<TransactionFilters>({ page: 1, page_size: 20 })
  const [search, setSearch] = useState('')

  const load = useCallback(async () => {
    setIsLoading(true)
    setError('')
    try {
      const result = await transactionService.list(filters)
      setData(result)
    } catch {
      setError('Failed to load transactions.')
    } finally {
      setIsLoading(false)
    }
  }, [filters])

  useEffect(() => { load() }, [load])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setFilters(f => ({ ...f, search: search || undefined, page: 1 }))
  }

  return (
    <div className="p-6 space-y-4 animate-fade-in">
      <div>
        <h1 className="text-xl font-bold text-slate-100">Transactions</h1>
        <p className="text-sm text-slate-400 mt-0.5">Payment transaction records</p>
      </div>

      {/* Filters */}
      <div className="card p-4 flex flex-wrap items-center gap-3">
        <form id="transaction-search-form" onSubmit={handleSearch} className="flex gap-2 flex-1 min-w-48">
          <input
            id="transaction-search-input"
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search payment ID, order ID…"
            className="input flex-1"
          />
          <button id="transaction-search-btn" type="submit" className="btn-primary px-4">Search</button>
        </form>

        <select
          id="transaction-status-filter"
          className="input w-44"
          value={filters.status || ''}
          onChange={(e) => setFilters(f => ({ ...f, status: (e.target.value as TransactionStatus) || undefined, page: 1 }))}
        >
          <option value="">All Statuses</option>
          {STATUSES.map(s => <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>)}
        </select>

        {(filters.status || filters.search) && (
          <button
            id="clear-filters-btn"
            className="btn-secondary text-xs"
            onClick={() => { setFilters({ page: 1, page_size: 20 }); setSearch('') }}
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Table */}
      <div className="card">
        {error ? (
          <ErrorState message={error} onRetry={load} />
        ) : isLoading ? (
          <LoadingSkeleton rows={8} cols={7} />
        ) : !data || data.items.length === 0 ? (
          <EmptyState
            title="No transactions found"
            description="No transactions match your current filters."
          />
        ) : (
          <>
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Payment ID</th>
                    <th>Order ID</th>
                    <th>Amount</th>
                    <th>Fee</th>
                    <th>Status</th>
                    <th>Method</th>
                    <th>Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((tx) => (
                    <tr key={tx.id} onClick={() => navigate(`/transactions/${tx.id}`)}>
                      <td className="font-mono text-brand-400 text-xs">{tx.payment_id}</td>
                      <td className="font-mono text-xs text-slate-400">{tx.order_id}</td>
                      <td className="text-money">{formatCurrency(tx.amount)}</td>
                      <td className="text-slate-400">{formatCurrency(tx.fee)}</td>
                      <td><StatusBadge status={tx.status} /></td>
                      <td className="text-slate-400">{tx.payment_method || '—'}</td>
                      <td className="text-slate-400 text-xs">{formatDateTime(tx.transaction_timestamp)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              page={data.page}
              pages={data.pages}
              total={data.total}
              page_size={data.page_size}
              onPageChange={(p) => setFilters(f => ({ ...f, page: p }))}
            />
          </>
        )}
      </div>
    </div>
  )
}

export default TransactionsPage
