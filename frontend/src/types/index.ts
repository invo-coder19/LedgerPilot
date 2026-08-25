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
