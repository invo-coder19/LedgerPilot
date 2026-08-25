import React from 'react'
import type { TransactionStatus } from '../types'

type StatusType = TransactionStatus | 'ISSUED' | 'PAID' | 'PARTIALLY_PAID' | 'OVERDUE' | 'CANCELLED' | 'PROCESSED' | 'CREDIT' | 'DEBIT' | string

const STATUS_STYLES: Record<string, string> = {
  SUCCESS:        'bg-green-500/10 text-green-400 border border-green-500/20',
  PAID:           'bg-green-500/10 text-green-400 border border-green-500/20',
  PROCESSED:      'bg-green-500/10 text-green-400 border border-green-500/20',
  CREDIT:         'bg-green-500/10 text-green-400 border border-green-500/20',
  FAILED:         'bg-red-500/10 text-red-400 border border-red-500/20',
  CANCELLED:      'bg-red-500/10 text-red-400 border border-red-500/20',
  REFUNDED:       'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20',
  PARTIAL_REFUND: 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20',
  PARTIALLY_PAID: 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20',
  PENDING:        'bg-blue-500/10 text-blue-400 border border-blue-500/20',
  ISSUED:         'bg-blue-500/10 text-blue-400 border border-blue-500/20',
  OVERDUE:        'bg-orange-500/10 text-orange-400 border border-orange-500/20',
  DEBIT:          'bg-orange-500/10 text-orange-400 border border-orange-500/20',
}

const STATUS_LABELS: Record<string, string> = {
  PARTIAL_REFUND: 'Partial Refund',
  PARTIALLY_PAID: 'Partially Paid',
}

interface StatusBadgeProps {
  status: StatusType
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const style = STATUS_STYLES[status] || 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
  const label = STATUS_LABELS[status] || status.replace(/_/g, ' ')

  return (
    <span className={`badge ${style}`}>
      {label}
    </span>
  )
}

export default StatusBadge
