import api from './api'
import type { AuditLog, AuditAction, PaginatedResponse } from '../types'

export const auditService = {
  async list(params: { action?: AuditAction; entity_type?: string; page?: number; page_size?: number } = {}): Promise<PaginatedResponse<AuditLog>> {
    const { data } = await api.get<PaginatedResponse<AuditLog>>('/audit-logs', { params })
    return data
  },

  async getById(id: string): Promise<AuditLog> {
    const { data } = await api.get<AuditLog>(`/audit-logs/${id}`)
    return data
  },
}
