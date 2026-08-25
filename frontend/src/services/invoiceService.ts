import api from './api'
import type { Invoice, InvoiceStatus, PaginatedResponse } from '../types'

export const invoiceService = {
  async list(params: { status?: InvoiceStatus; search?: string; page?: number; page_size?: number } = {}): Promise<PaginatedResponse<Invoice>> {
    const { data } = await api.get<PaginatedResponse<Invoice>>('/invoices', { params })
    return data
  },

  async getById(id: string): Promise<Invoice> {
    const { data } = await api.get<Invoice>(`/invoices/${id}`)
    return data
  },
}
