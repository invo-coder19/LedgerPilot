import api from './api'
import type { DashboardSummary, ExceptionTrendPoint, StatusDistributionItem, TransactionVolumePoint } from '../types'

export const dashboardService = {
  async getSummary(): Promise<DashboardSummary> {
    const { data } = await api.get<DashboardSummary>('/dashboard/summary')
    return data
  },

  async getTransactionVolume(): Promise<TransactionVolumePoint[]> {
    const { data } = await api.get<TransactionVolumePoint[]>('/dashboard/transaction-volume')
    return data
  },

  async getStatusDistribution(): Promise<StatusDistributionItem[]> {
    const { data } = await api.get<StatusDistributionItem[]>('/dashboard/status-distribution')
    return data
  },

  async getExceptionTrend(): Promise<ExceptionTrendPoint[]> {
    const { data } = await api.get<ExceptionTrendPoint[]>('/dashboard/exception-trend')
    return data
  },
}
