import React, { useEffect, useState, useCallback } from 'react'
import StatusBadge from '../components/StatusBadge'
import Pagination from '../components/Pagination'
import LoadingSkeleton from '../components/LoadingSkeleton'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import { bankTransactionService } from '../services/bankTransactionService'
import type { BankTransaction, BankTransactionType, PaginatedResponse } from '../types'
import { formatCurrency, formatDate } from '../utils/format'

const BankTransactionsPage: React.FC = () => {
  const [data, setData] = useState<PaginatedResponse<BankTransaction> | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [typeFilter, setTypeFilter] = useState<BankTransactionType | ''>('')
  const [page, setPage] = useState(1)

  const load = useCallback(async () => {
    setIsLoading(true)
    setError('')
    try {
      const result = await bankTransactionService.list({
        transaction_type: typeFilter || undefined, page, page_size: 20,
      })
      setData(result)
    } catch { setError('Failed to load bank transactions.') }
    finally { setIsLoading(false) }
  }, [typeFilter, page])

  useEffect(() => { load() }, [load])

  return (
    <div className="p-6 space-y-4 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Bank Ledger</h1>
          <p className="text-sm text-slate-400 mt-0.5">Bank account transaction records</p>
        </div>
        <select id="bank-type-filter" className="input w-44"
          value={typeFilter}
          onChange={(e) => { setTypeFilter(e.target.value as BankTransactionType | ''); setPage(1) }}>
          <option value="">All Types</option>
          <option value="CREDIT">Credit</option>
          <option value="DEBIT">Debit</option>
        </select>
      </div>

      <div className="card">
        {error ? <ErrorState message={error} onRetry={load} />
          : isLoading ? <LoadingSkeleton rows={8} cols={6} />
          : !data || data.items.length === 0 ? (
            <EmptyState title="No bank transactions found" description="No bank transactions match your current filters." />
          ) : (
            <>
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Bank Txn ID</th>
                      <th>Reference</th>
                      <th>Amount</th>
                      <th>Type</th>
                      <th>Date</th>
                      <th>Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((bt) => (
                      <tr key={bt.id}>
                        <td className="font-mono text-brand-400 text-xs">{bt.bank_transaction_id}</td>
                        <td className="font-mono text-xs text-slate-400">{bt.reference || '—'}</td>
                        <td className="text-money">{formatCurrency(bt.amount)}</td>
                        <td><StatusBadge status={bt.transaction_type} /></td>
                        <td className="text-slate-400">{formatDate(bt.transaction_date)}</td>
                        <td className="text-slate-400 max-w-xs truncate">{bt.description || '—'}</td>
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

export default BankTransactionsPage
