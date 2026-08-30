import api from './api'
import type { SystemHealth } from '../types'

export const healthService = {
  getDetailed: (): Promise<SystemHealth> =>
    api.get('/health/detailed').then(r => r.data),

  getLiveness: (): Promise<{ status: string }> =>
    api.get('/health/live').then(r => r.data),

  getReadiness: (): Promise<{ status: string; database?: unknown }> =>
    api.get('/health/ready').then(r => r.data),
}
