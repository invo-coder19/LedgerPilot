import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import StatusBadge from '../components/StatusBadge'
import SeverityBadge from '../components/SeverityBadge'
import ErrorState from '../components/ErrorState'
import RoleGuard from '../auth/RoleGuard'
import { exceptionService } from '../services/exceptionService'
import type { FinancialException, ExceptionStatus } from '../types'
import { formatCurrency, formatDateTime, getErrorMessage } from '../utils/format'

const STATUS_ACTIONS: Array<{ status: ExceptionStatus; label: string; style: string }> = [
  { status: 'IN_REVIEW', label: 'Mark In Review', style: 'btn-secondary' },
  { status: 'RESOLVED', label: 'Resolve', style: 'btn-primary' },
  { status: 'DISMISSED', label: 'Dismiss', style: 'btn-danger' },
]

const ExceptionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [exc, setExc] = useState<FinancialException | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [updating, setUpdating] = useState(false)
  const [error, setError] = useState('')
  const [updateError, setUpdateError] = useState('')
  const [updateSuccess, setUpdateSuccess] = useState('')

  useEffect(() => {
    if (!id) return
    exceptionService.getById(id)
      .then(setExc)
      .catch(() => setError('Exception not found.'))
      .finally(() => setIsLoading(false))
  }, [id])

  const handleStatusUpdate = async (status: ExceptionStatus) => {
    if (!id) return
    setUpdating(true)
    setUpdateError('')
    setUpdateSuccess('')
    try {
      const updated = await exceptionService.updateStatus(id, status)
      setExc(updated)
      setUpdateSuccess(`Status updated to ${status.replace(/_/g, ' ')}`)
    } catch (err) {
      setUpdateError(getErrorMessage(err))
    } finally {
      setUpdating(false)
    }
  }

  if (isLoading) return <div className="p-6"><div className="skeleton h-96 rounded-xl w-full" /></div>
  if (error || !exc) return <div className="p-6"><ErrorState message={error || 'Not found'} onRetry={() => navigate(-1)} /></div>

  return (
    <div className="p-6 max-w-3xl animate-fade-in space-y-4">
      <button id="exception-back-btn" onClick={() => navigate(-1)} className="btn-secondary text-xs">
        ← Back to Exceptions
      </button>

      <div className="card p-6 space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-lg font-bold text-slate-100">Exception Detail</h1>
            <p className="text-xs text-slate-500 font-mono mt-0.5">{exc.id}</p>
          </div>
          <div className="flex items-center gap-2">
            <SeverityBadge severity={exc.severity} />
            <StatusBadge status={exc.status} />
          </div>
        </div>

        {/* Key info */}
        <div className="grid grid-cols-2 gap-6">
          <div>
            <p className="label">Exception Type</p>
            <p className="text-sm text-slate-200">{exc.exception_type.replace(/_/g, ' ')}</p>
          </div>
          <div>
            <p className="label">Amount Involved</p>
            <p className="text-sm text-money">{formatCurrency(exc.amount)}</p>
          </div>
          <div>
            <p className="label">Source Type</p>
            <p className="text-sm text-slate-200 capitalize">{exc.source_type}</p>
          </div>
          <div>
            <p className="label">Source ID</p>
            <p className="text-sm font-mono text-slate-300">{exc.source_id}</p>
          </div>
          <div>
            <p className="label">Created At</p>
            <p className="text-sm text-slate-400">{formatDateTime(exc.created_at)}</p>
          </div>
          <div>
            <p className="label">Updated At</p>
            <p className="text-sm text-slate-400">{formatDateTime(exc.updated_at)}</p>
          </div>
        </div>

        {/* Description */}
        <div className="p-4 bg-surface rounded-xl">
          <p className="label mb-2">Description</p>
          <p className="text-sm text-slate-300 leading-relaxed">{exc.description}</p>
        </div>

        {/* Status actions */}
        <RoleGuard
          roles={['ADMIN', 'FINANCE_MANAGER', 'FINANCE_ANALYST']}
          fallback={
            <p className="text-xs text-slate-500 italic">
              You do not have permission to change exception status.
            </p>
          }
        >
          <div className="border-t border-surface-border pt-4">
            <p className="label mb-3">Update Status</p>
            {updateSuccess && (
              <div className="mb-3 px-3 py-2 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400 text-xs">
                ✓ {updateSuccess}
              </div>
            )}
            {updateError && (
              <div className="mb-3 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
                {updateError}
              </div>
            )}
            <div className="flex flex-wrap gap-2">
              {STATUS_ACTIONS.filter(a => a.status !== exc.status).map((action) => (
                <button
                  key={action.status}
                  id={`exception-action-${action.status.toLowerCase()}`}
                  onClick={() => handleStatusUpdate(action.status)}
                  disabled={updating}
                  className={`${action.style} text-sm disabled:opacity-50`}
                >
                  {updating ? '…' : action.label}
                </button>
              ))}
            </div>
          </div>
        </RoleGuard>

        {/* AI Investigation Placeholder */}
        <div className="border border-dashed border-surface-border rounded-xl p-5 bg-surface/50">
          <div className="flex items-center gap-2 mb-2">
            <svg className="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            <h3 className="text-sm font-medium text-slate-400">AI Investigation</h3>
            <span className="badge bg-slate-500/10 text-slate-500 border border-slate-500/20">Available in Phase 3</span>
          </div>
          <p className="text-xs text-slate-600">
            Automated root cause analysis, suggested remediation, and confidence scoring will be available
            once the Intelligence Layer (Phase 3) is deployed.
          </p>
        </div>
      </div>
    </div>
  )
}

export default ExceptionDetailPage
