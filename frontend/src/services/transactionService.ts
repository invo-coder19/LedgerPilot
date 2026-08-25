import api from './api'
import type { PaginatedResponse, Transaction, TransactionStatus } from '../types'

export interface TransactionFilters {
  status?: TransactionStatus
  search?: string
  date_from?: string
  date_to?: string
  page?: number
  page_size?: number
}

export const transactionService = {
  async list(filters: TransactionFilters = {}): Promise<PaginatedResponse<Transaction>> {
    const { data } = await api.get<PaginatedResponse<Transaction>>('/transactions', {
      params: filters,
    })
    return data
  },

  async getById(id: string): Promise<Transaction> {
    const { data } = await api.get<Transaction>(`/transactions/${id}`)
    return data
  },
}
