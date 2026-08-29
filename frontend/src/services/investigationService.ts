import { apiClient } from './api'
import type {
  StartInvestigationResponse,
  InvestigationRun,
  InvestigationStep,
  CopilotRequest,
  CopilotResponse,
} from '../types'

const BASE = '/api/v1'

export const investigationService = {
  /** Start an AI investigation for an exception */
  async investigate(exceptionId: string): Promise<StartInvestigationResponse> {
    const res = await apiClient.post<StartInvestigationResponse>(
      `${BASE}/exceptions/${exceptionId}/investigate`
    )
    return res.data
  },

  /** Get a full investigation run with result */
  async getInvestigation(investigationId: string): Promise<InvestigationRun> {
    const res = await apiClient.get<InvestigationRun>(
      `${BASE}/investigations/${investigationId}`
    )
    return res.data
  },

  /** Get investigation timeline steps */
  async getSteps(investigationId: string): Promise<InvestigationStep[]> {
    const res = await apiClient.get<InvestigationStep[]>(
      `${BASE}/investigations/${investigationId}/steps`
    )
    return res.data
  },

  /** List all investigations for an exception */
  async listForException(exceptionId: string): Promise<InvestigationRun[]> {
    const res = await apiClient.get<InvestigationRun[]>(
      `${BASE}/exceptions/${exceptionId}/investigations`
    )
    return res.data
  },

  /** Ask the Finance Copilot */
  async askCopilot(request: CopilotRequest): Promise<CopilotResponse> {
    const res = await apiClient.post<CopilotResponse>(`${BASE}/copilot/ask`, request)
    return res.data
  },
}
