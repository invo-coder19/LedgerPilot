import React, { useEffect, useState, useCallback } from 'react'
import Pagination from '../components/Pagination'
import LoadingSkeleton from '../components/LoadingSkeleton'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import { auditService } from '../services/auditService'
import type { AuditLog, AuditAction, PaginatedResponse } from '../types'
import { formatDateTime } from '../utils/format'

const ACTIONS: AuditAction[] = [
  'LOGIN', 'LOGOUT', 'VIEW_TRANSACTION', 'VIEW_INVOICE', 'VIEW_SETTLEMENT',
  'VIEW_BANK_TRANSACTION', 'VIEW_EXCEPTION', 'UPDATE_EXCEPTION',
  'APPROVE_ACTION', 'REJECT_ACTION', 'VIEW_AUDIT_LOG', 'VIEW_DASHBOARD',
]

const ACTION_COLORS: Record<string, string> = {
  LOGIN: 'text-green-400',
  LOGOUT: 'text-slate-400',
  UPDATE_EXCEPTION: 'text-orange-400',
  APPROVE_ACTION: 'text-green-400',
  REJECT_ACTION: 'text-red-400',
}

const AuditLogPage: React.FC = () => {
  const [data, setData] = useState<PaginatedResponse<AuditLog> | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionFilter, setActionFilter] = useState<AuditAction | ''>('')
  const [page, setPage] = useState(1)
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null)

  const load = useCallback(async () => {
    setIsLoading(true)
    setError('')
    try {
      const result = await auditService.list({
        action: actionFilter || undefined, page, page_size: 20,
      })
      setData(result)
    } catch { setError('Failed to load audit logs. You may not have permission to view this page.') }
    finally { setIsLoading(false) }
  }, [actionFilter, page])

  useEffect(() => { load() }, [load])

  return (
    <div className="p-6 space-y-4 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Audit Log</h1>
          <p className="text-sm text-slate-400 mt-0.5">Chronological record of all system events</p>
        </div>
        <select id="audit-action-filter" className="input w-56"
          value={actionFilter}
          onChange={(e) => { setActionFilter(e.target.value as AuditAction | ''); setPage(1) }}>
          <option value="">All Actions</option>
          {ACTIONS.map(a => <option key={a} value={a}>{a.replace(/_/g, ' ')}</option>)}
        </select>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 card">
          {error ? <ErrorState message={error} onRetry={load} />
            : isLoading ? <LoadingSkeleton rows={10} cols={4} />
            : !data || data.items.length === 0 ? (
              <EmptyState title="No audit events found" description="No events match your current filters." />
            ) : (
              <>
                <div className="table-wrapper">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Timestamp</th>
                        <th>Action</th>
                        <th>Entity</th>
                        <th>Description</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.items.map((log) => (
                        <tr key={log.id} onClick={() => setSelectedLog(log)}>
                          <td className="text-xs text-slate-400">{formatDateTime(log.created_at)}</td>
                          <td>
                            <span className={`text-xs font-mono font-medium ${ACTION_COLORS[log.action] || 'text-brand-400'}`}>
                              {log.action}
                            </span>
                          </td>
                          <td className="text-xs text-slate-400">
                            {log.entity_type ? `${log.entity_type}` : '—'}
                          </td>
                          <td className="text-xs text-slate-300 max-w-xs truncate">{log.description}</td>
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

        {/* Detail panel */}
        <div className="card p-5">
          {selectedLog ? (
            <div className="space-y-3">
              <h2 className="text-sm font-semibold text-slate-200">Event Detail</h2>
              <div>
                <p className="label">Action</p>
                <p className={`text-sm font-mono ${ACTION_COLORS[selectedLog.action] || 'text-brand-400'}`}>
                  {selectedLog.action}
                </p>
              </div>
              <div>
                <p className="label">Description</p>
                <p className="text-xs text-slate-300">{selectedLog.description}</p>
              </div>
              <div>
                <p className="label">Timestamp</p>
                <p className="text-xs text-slate-400">{formatDateTime(selectedLog.created_at)}</p>
              </div>
              {selectedLog.entity_type && (
                <div>
                  <p className="label">Entity</p>
                  <p className="text-xs text-slate-300">{selectedLog.entity_type}: {selectedLog.entity_id}</p>
                </div>
              )}
              {selectedLog.metadata_ && (
                <div>
                  <p className="label">Metadata</p>
                  <pre className="text-xs text-slate-400 bg-surface rounded p-2 overflow-auto">
                    {JSON.stringify(selectedLog.metadata_, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-40 text-center">
              <p className="text-sm text-slate-500">Select an event to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default AuditLogPage
