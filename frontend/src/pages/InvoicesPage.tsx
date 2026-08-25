import React, { useEffect, useState, useCallback } from 'react'
import StatusBadge from '../components/StatusBadge'
import Pagination from '../components/Pagination'
import LoadingSkeleton from '../components/LoadingSkeleton'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import { invoiceService } from '../services/invoiceService'
import type { Invoice, InvoiceStatus, PaginatedResponse } from '../types'
import { formatCurrency, formatDate } from '../utils/format'

const STATUSES: InvoiceStatus[] = ['ISSUED', 'PAID', 'PARTIALLY_PAID', 'OVERDUE', 'CANCELLED']

const InvoicesPage: React.FC = () => {
  const [data, setData] = useState<PaginatedResponse<Invoice> | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | ''>('')
  const [page, setPage] = useState(1)

  const load = useCallback(async () => {
    setIsLoading(true)
    setError('')
    try {
      const result = await invoiceService.list({
        status: statusFilter || undefined,
        page, page_size: 20,
      })
      setData(result)
    } catch { setError('Failed to load invoices.') }
    finally { setIsLoading(false) }
  }, [statusFilter, page])

  useEffect(() => { load() }, [load])

  return (
    <div className="p-6 space-y-4 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Invoices</h1>
          <p className="text-sm text-slate-400 mt-0.5">Invoice records and payment status</p>
        </div>
        <select
          id="invoice-status-filter"
          className="input w-44"
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value as InvoiceStatus | ''); setPage(1) }}
        >
          <option value="">All Statuses</option>
          {STATUSES.map(s => <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>)}
        </select>
      </div>

      <div className="card">
        {error ? <ErrorState message={error} onRetry={load} />
          : isLoading ? <LoadingSkeleton rows={8} cols={6} />
          : !data || data.items.length === 0 ? (
            <EmptyState title="No invoices found" description="No invoices match your current filters." />
          ) : (
            <>
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Invoice ID</th>
                      <th>Customer</th>
                      <th>Amount</th>
                      <th>Tax</th>
                      <th>Status</th>
                      <th>Invoice Date</th>
                      <th>Due Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((inv) => (
                      <tr key={inv.id}>
                        <td className="font-mono text-brand-400 text-xs">{inv.invoice_id}</td>
                        <td className="text-slate-400">{inv.customer_id || '—'}</td>
                        <td className="text-money">{formatCurrency(inv.amount)}</td>
                        <td className="text-slate-400">{formatCurrency(inv.tax)}</td>
                        <td><StatusBadge status={inv.status} /></td>
                        <td className="text-slate-400">{formatDate(inv.invoice_date)}</td>
                        <td className="text-slate-400">{formatDate(inv.due_date)}</td>
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

export default InvoicesPage
