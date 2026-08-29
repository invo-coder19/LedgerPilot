// TypeScript interfaces matching backend Pydantic schemas

export type Role = 'ADMIN' | 'FINANCE_MANAGER' | 'FINANCE_ANALYST' | 'VIEWER'

export type TransactionStatus = 'SUCCESS' | 'FAILED' | 'REFUNDED' | 'PARTIAL_REFUND' | 'PENDING'
export type InvoiceStatus = 'ISSUED' | 'PAID' | 'PARTIALLY_PAID' | 'OVERDUE' | 'CANCELLED'
export type SettlementStatus = 'PENDING' | 'PROCESSED' | 'FAILED'
export type BankTransactionType = 'CREDIT' | 'DEBIT'
export type ExceptionType = 'AMOUNT_MISMATCH' | 'MISSING_INVOICE' | 'MISSING_SETTLEMENT' | 'DUPLICATE' | 'REFUND_MISMATCH' | 'UNKNOWN'
export type ExceptionSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
export type ExceptionStatus = 'OPEN' | 'IN_REVIEW' | 'RESOLVED' | 'DISMISSED'
export type AuditAction = 'LOGIN' | 'LOGOUT' | 'VIEW_TRANSACTION' | 'VIEW_INVOICE' | 'VIEW_SETTLEMENT' | 'VIEW_BANK_TRANSACTION' | 'VIEW_EXCEPTION' | 'UPDATE_EXCEPTION' | 'APPROVE_ACTION' | 'REJECT_ACTION' | 'VIEW_AUDIT_LOG' | 'VIEW_DASHBOARD'

// ── Auth ──────────────────────────────────────────────────────────────────────
export interface User {
  id: string
  email: string
  full_name: string
  role: Role
  is_active: boolean
}

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

// ── Pagination ────────────────────────────────────────────────────────────────
export interface PaginatedResponse<T> {
  total: number
  page: number
  page_size: number
  pages: number
  items: T[]
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
export interface DashboardSummary {
  total_transactions: number
  matched_transactions: number
  unmatched_transactions: number
  open_exceptions: number
  resolved_exceptions: number
  total_transaction_value: number
  total_settlement_value: number
}

export interface TransactionVolumePoint {
  date: string
  count: number
  amount: number
}

export interface StatusDistributionItem {
  status: string
  count: number
}

export interface ExceptionTrendPoint {
  date: string
  open: number
  resolved: number
}

// ── Transaction ───────────────────────────────────────────────────────────────
export interface Transaction {
  id: string
  merchant_id: string
  payment_id: string
  order_id: string
  customer_id: string | null
  amount: number
  fee: number
  tax: number
  status: TransactionStatus
  payment_method: string | null
  transaction_timestamp: string
  created_at: string
  updated_at: string
}

// ── Invoice ───────────────────────────────────────────────────────────────────
export interface Invoice {
  id: string
  merchant_id: string
  invoice_id: string
  customer_id: string | null
  amount: number
  tax: number
  status: InvoiceStatus
  invoice_date: string
  due_date: string
  payment_reference: string | null
  created_at: string
  updated_at: string
}

// ── Settlement ────────────────────────────────────────────────────────────────
export interface Settlement {
  id: string
  merchant_id: string
  settlement_id: string
  payment_id: string
  settlement_amount: number
  fee: number
  settlement_date: string
  status: SettlementStatus
  created_at: string
  updated_at: string
}

// ── Bank Transaction ──────────────────────────────────────────────────────────
export interface BankTransaction {
  id: string
  merchant_id: string
  bank_transaction_id: string
  reference: string | null
  amount: number
  transaction_type: BankTransactionType
  transaction_date: string
  description: string | null
  created_at: string
  updated_at: string
}

// ── Exception ─────────────────────────────────────────────────────────────────
export interface FinancialException {
  id: string
  merchant_id: string
  source_type: string
  source_id: string
  exception_type: ExceptionType
  severity: ExceptionSeverity
  amount: number | null
  description: string
  status: ExceptionStatus
  created_at: string
  updated_at: string
}

// ── Audit Log ─────────────────────────────────────────────────────────────────
export interface AuditLog {
  id: string
  user_id: string | null
  merchant_id: string | null
  action: AuditAction
  entity_type: string | null
  entity_id: string | null
  description: string
  metadata_: Record<string, unknown> | null
  created_at: string
}

// ── Phase 3A: ML & Intelligence ───────────────────────────────────────────────

export interface ExceptionPrediction {
  id: string
  predicted_type: string
  confidence: number  // [0, 1]
  model_version: string
  top_alternatives: Array<{ label: string; confidence: number }>
  created_at: string
}

export interface AnomalyPrediction {
  id: string
  is_anomaly: boolean
  anomaly_score: number  // [0, 1]
  model_version: string
  created_at: string
}

export interface MLAnalysisResponse {
  exception_id: string
  classifier: ExceptionPrediction | null
  anomaly: AnomalyPrediction | null
  models_available: boolean
  message: string
}

export interface EvidenceDocument {
  id: string
  merchant_id: string | null
  source_type: string
  source_id: string | null
  title: string
  content: string
  metadata: Record<string, unknown> | null
  trust_level: string
  similarity_score: number | null
  created_at: string | null
}

export interface EvidenceCounts {
  transactions: number
  settlements: number
  invoices: number
  bank_transactions: number
  finance_rules: number
  historical_cases: number
  total: number
}

export interface EvidenceBundleResponse {
  exception_id: string
  transaction_evidence: EvidenceDocument[]
  settlement_evidence: EvidenceDocument[]
  invoice_evidence: EvidenceDocument[]
  bank_evidence: EvidenceDocument[]
  finance_rules: EvidenceDocument[]
  historical_cases: EvidenceDocument[]
  counts: EvidenceCounts
}

export interface EvidenceSearchResponse {
  query: string
  results: EvidenceDocument[]
  total: number
}

export interface MLAgreement {
  deterministic_type: string
  ml_type: string
  agree: boolean
  note: string
}

export interface IntelligenceContext {
  exception_id: string
  deterministic_analysis: {
    exception_type: string
    severity: string
    source_type: string
    source_id: string
    description: string
    status: string
  }
  ml_prediction: {
    id: string
    predicted_type: string
    confidence: number
    model_version: string
    top_alternatives: Array<{ label: string; confidence: number }>
    created_at: string
  } | null
  anomaly_analysis: {
    id: string
    is_anomaly: boolean
    anomaly_score: number
    model_version: string
    created_at: string
  } | null
  ml_agreement: MLAgreement | null
  models_available: boolean
  evidence: EvidenceDocument[]
  evidence_counts: EvidenceCounts
  transaction_evidence: EvidenceDocument[]
  settlement_evidence: EvidenceDocument[]
  invoice_evidence: EvidenceDocument[]
  bank_evidence: EvidenceDocument[]
  finance_rules: EvidenceDocument[]
  historical_cases: EvidenceDocument[]
  phase_3b_ready: boolean
}

// ── Phase 3B: AI Investigation ────────────────────────────────────────────────

export interface InvestigationResult {
  exception_id: string
  root_cause: string
  confidence: number
  confidence_band: 'HIGH' | 'MEDIUM' | 'LOW'
  conclusion: string
  observed_facts: string[]
  inferences: string[]
  evidence_ids: string[]
  recommendation: string
  next_steps: string[]
  uncertainties: string[]
  requires_human_review: boolean
  contradiction_detected: boolean
}

export interface InvestigationStep {
  id: string
  step_name: string
  tool_name: string | null
  input_summary: string | null
  output_summary: string | null
  duration_ms: number | null
  created_at: string
}

export interface InvestigationRun {
  id: string
  exception_id: string
  merchant_id: string | null
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'
  started_at: string
  completed_at: string | null
  model_provider: string | null
  model_name: string | null
  final_result: InvestigationResult | null
  final_confidence: number | null
  confidence_band: string | null
  requires_human: boolean
  error_message: string | null
  duration_ms: number | null
  steps: InvestigationStep[]
}

export interface StartInvestigationResponse {
  investigation_id: string
  status: string
  result: InvestigationResult | null
  error: string | null
  message: string
}

export interface CopilotRequest {
  question: string
}

export interface CopilotResponse {
  answer: string
  evidence_used: Array<{ id: string; title: string; source_type: string }>
  disclaimer: string
}
