import api from './api'
import type { FinancialException, ExceptionStatus, ExceptionSeverity, ExceptionType, PaginatedResponse } from '../types'

export interface ExceptionFilters {
  status?: ExceptionStatus
  severity?: ExceptionSeverity
  exception_type?: ExceptionType
  page?: number
  page_size?: number
}

export const exceptionService = {
  async list(filters: ExceptionFilters = {}): Promise<PaginatedResponse<FinancialException>> {
    const { data } = await api.get<PaginatedResponse<FinancialException>>('/exceptions', {
      params: filters,
    })
    return data
  },

  async getById(id: string): Promise<FinancialException> {
    const { data } = await api.get<FinancialException>(`/exceptions/${id}`)
    return data
  },

  async updateStatus(id: string, status: ExceptionStatus): Promise<FinancialException> {
    const { data } = await api.patch<FinancialException>(`/exceptions/${id}`, { status })
    return data
  },
}
