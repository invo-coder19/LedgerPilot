/**
 * Intelligence service — calls Phase 3A API routes.
 */

import api from './api'
import type {
  MLAnalysisResponse,
  EvidenceBundleResponse,
  EvidenceSearchResponse,
  IntelligenceContext,
  EvidenceDocument,
} from '../types'

const BASE = '/api/v1/intelligence'

export const intelligenceService = {
  /** Trigger ML inference (classifier + anomaly detector) for an exception. */
  runMlAnalysis: async (exceptionId: string): Promise<MLAnalysisResponse> => {
    const res = await api.post<MLAnalysisResponse>(
      `${BASE}/exceptions/${exceptionId}/run-ml`
    )
    return res.data
  },

  /** Get full intelligence context (ML + evidence) for Phase 3B. */
  getIntelligenceContext: async (exceptionId: string): Promise<IntelligenceContext> => {
    const res = await api.get<IntelligenceContext>(
      `${BASE}/exceptions/${exceptionId}/intelligence-context`
    )
    return res.data
  },

  /** Get evidence bundle for an exception. */
  getEvidenceBundle: async (exceptionId: string): Promise<EvidenceBundleResponse> => {
    const res = await api.get<EvidenceBundleResponse>(
      `${BASE}/exceptions/${exceptionId}/evidence`
    )
    return res.data
  },

  /** Semantic + hybrid evidence search. */
  searchEvidence: async (
    query: string,
    topK = 7,
    sourceTypes?: string[]
  ): Promise<EvidenceSearchResponse> => {
    const res = await api.post<EvidenceSearchResponse>(`${BASE}/evidence/search`, {
      query,
      top_k: topK,
      source_types: sourceTypes ?? null,
    })
    return res.data
  },

  /** Get a single evidence document by ID. */
  getEvidenceDocument: async (evidenceId: string): Promise<EvidenceDocument> => {
    const res = await api.get<EvidenceDocument>(`${BASE}/evidence/${evidenceId}`)
    return res.data
  },
}
