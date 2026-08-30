import api from './api'
import type { EvaluationSummary, EvaluationRun } from '../types'

export const evaluationService = {
  getSummary: (): Promise<EvaluationSummary> =>
    api.get('/evaluation/summary').then(r => r.data),

  listRuns: (): Promise<EvaluationRun[]> =>
    api.get('/evaluation/runs').then(r => r.data),

  getRun: (id: string): Promise<EvaluationRun & { metrics: Record<string, { value: number; category: string }> }> =>
    api.get(`/evaluation/runs/${id}`).then(r => r.data),

  startRun: (datasetName: string, version = 'v1'): Promise<EvaluationRun> =>
    api.post('/evaluation/runs', { dataset_name: datasetName, version }).then(r => r.data),

  getReport: (runId: string, format: 'json' | 'markdown' = 'json'): Promise<unknown> =>
    api.get(`/evaluation/runs/${runId}/report`, { params: { format } }).then(r => r.data),

  compareRuns: (runA: string, runB: string): Promise<unknown> =>
    api.get('/evaluation/compare', { params: { run_a: runA, run_b: runB } }).then(r => r.data),

  generateDataset: (params: {
    records?: number
    seed?: number
    name?: string
    version?: string
  }): Promise<unknown> =>
    api.post('/evaluation/datasets', params).then(r => r.data),
}
