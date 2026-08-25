import api from './api'
import type { Settlement, SettlementStatus, PaginatedResponse } from '../types'

export const settlementService = {
  async list(params: { status?: SettlementStatus; page?: number; page_size?: number } = {}): Promise<PaginatedResponse<Settlement>> {
    const { data } = await api.get<PaginatedResponse<Settlement>>('/settlements', { params })
    return data
  },

  async getById(id: string): Promise<Settlement> {
    const { data } = await api.get<Settlement>(`/settlements/${id}`)
    return data
  },
}
