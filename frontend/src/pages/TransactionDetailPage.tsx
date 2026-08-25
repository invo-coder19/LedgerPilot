import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import StatusBadge from '../components/StatusBadge'
import ErrorState from '../components/ErrorState'
import { transactionService } from '../services/transactionService'
import type { Transaction } from '../types'
import { formatCurrency, formatDateTime } from '../utils/format'

const TransactionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [tx, setTx] = useState<Transaction | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    transactionService.getById(id)
      .then(setTx)
      .catch(() => setError('Transaction not found.'))
      .finally(() => setIsLoading(false))
  }, [id])

  if (isLoading) return (
    <div className="p-6"><div className="skeleton h-96 rounded-xl w-full" /></div>
  )
  if (error || !tx) return (
    <div className="p-6"><ErrorState message={error || 'Not found'} onRetry={() => navigate(-1)} /></div>
  )

  const fields = [
    { label: 'Payment ID', value: tx.payment_id, mono: true },
    { label: 'Order ID', value: tx.order_id, mono: true },
    { label: 'Customer ID', value: tx.customer_id || '—' },
    { label: 'Payment Method', value: tx.payment_method || '—' },
    { label: 'Transaction Date', value: formatDateTime(tx.transaction_timestamp) },
    { label: 'Created At', value: formatDateTime(tx.created_at) },
  ]

  return (
    <div className="p-6 max-w-3xl animate-fade-in">
      <button id="back-btn" onClick={() => navigate(-1)} className="btn-secondary mb-5 text-xs">
        ← Back to Transactions
      </button>

      <div className="card p-6">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-lg font-bold text-slate-100">Transaction Detail</h1>
            <p className="text-xs text-slate-500 mt-0.5 font-mono">{tx.id}</p>
          </div>
          <StatusBadge status={tx.status} />
        </div>

        {/* Amount breakdown */}
        <div className="grid grid-cols-3 gap-4 mb-6 p-4 bg-surface rounded-xl">
          <div>
            <p className="label">Amount</p>
            <p className="text-xl font-semibold text-money">{formatCurrency(tx.amount)}</p>
          </div>
          <div>
            <p className="label">Fee</p>
            <p className="text-lg text-money text-slate-300">{formatCurrency(tx.fee)}</p>
          </div>
          <div>
            <p className="label">Tax</p>
            <p className="text-lg text-money text-slate-300">{formatCurrency(tx.tax)}</p>
          </div>
        </div>

        {/* Details grid */}
        <dl className="grid grid-cols-2 gap-x-6 gap-y-4">
          {fields.map(({ label, value, mono }) => (
            <div key={label}>
              <dt className="label">{label}</dt>
              <dd className={`text-sm text-slate-200 ${mono ? 'font-mono' : ''}`}>{value}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  )
}

export default TransactionDetailPage
