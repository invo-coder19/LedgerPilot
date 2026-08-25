import api from './api'
import type { BankTransaction, BankTransactionType, PaginatedResponse } from '../types'

export const bankTransactionService = {
  async list(params: { transaction_type?: BankTransactionType; page?: number; page_size?: number } = {}): Promise<PaginatedResponse<BankTransaction>> {
    const { data } = await api.get<PaginatedResponse<BankTransaction>>('/bank-transactions', { params })
    return data
  },

  async getById(id: string): Promise<BankTransaction> {
    const { data } = await api.get<BankTransaction>(`/bank-transactions/${id}`)
    return data
  },
}
