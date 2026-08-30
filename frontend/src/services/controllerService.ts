import api from './api'

// ── Controller Runs ──────────────────────────────────────────────────────────

export const createControllerRun = (data: { reconciliation_run_id?: string; dry_run?: boolean }) =>
  api.post('/controller/runs', data)

export const listControllerRuns = (page = 1, pageSize = 20) =>
  api.get('/controller/runs', { params: { page, page_size: pageSize } })

export const getControllerRun = (id: string) =>
  api.get(`/controller/runs/${id}`)

export const getRunDecisions = (runId: string, page = 1, pageSize = 20) =>
  api.get(`/controller/runs/${runId}/decisions`, { params: { page, page_size: pageSize } })

export const getDecision = (id: string) =>
  api.get(`/controller/decisions/${id}`)

// ── Approvals ────────────────────────────────────────────────────────────────

export const listApprovals = (status?: string, page = 1, pageSize = 20) =>
  api.get('/approvals', { params: { status, page, page_size: pageSize } })

export const getApproval = (id: string) =>
  api.get(`/approvals/${id}`)

export const approveAction = (id: string) =>
  api.post(`/approvals/${id}/approve`, {})

export const rejectAction = (id: string, reason: string) =>
  api.post(`/approvals/${id}/reject`, { reason })

// ── Policies ─────────────────────────────────────────────────────────────────

export const listPolicies = () =>
  api.get('/controller/policies')

export const getPolicy = (id: string) =>
  api.get(`/controller/policies/${id}`)

export const createPolicy = (data: { policy_id: string; name: string; description?: string; configuration: Record<string, unknown> }) =>
  api.post('/controller/policies', data)

export const updatePolicy = (id: string, data: { name?: string; description?: string; configuration?: Record<string, unknown> }) =>
  api.patch(`/controller/policies/${id}`, data)

// ── Actions ──────────────────────────────────────────────────────────────────

export const listActions = (page = 1, pageSize = 20) =>
  api.get('/actions', { params: { page, page_size: pageSize } })

export const getAction = (id: string) =>
  api.get(`/actions/${id}`)

export const rollbackAction = (id: string) =>
  api.post(`/actions/${id}/rollback`)

// ── Controller Config ────────────────────────────────────────────────────────

export const getControllerConfig = () =>
  api.get('/controller/config')

export const updateControllerConfig = (data: Record<string, unknown>) =>
  api.patch('/controller/config', data)

// ── Metrics ──────────────────────────────────────────────────────────────────

export const getControllerMetrics = () =>
  api.get('/controller/metrics')
