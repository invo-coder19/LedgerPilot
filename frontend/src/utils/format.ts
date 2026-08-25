/**
 * Format a number as Indian Rupee currency.
 */
export function formatCurrency(amount: number | string | null | undefined): string {
  if (amount === null || amount === undefined) return '—'
  const num = typeof amount === 'string' ? parseFloat(amount) : amount
  if (isNaN(num)) return '—'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num)
}

/**
 * Format a date string to a readable format.
 */
export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—'
  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date(dateStr))
}

/**
 * Format a datetime string to readable format with time.
 */
export function formatDateTime(dateStr: string | null | undefined): string {
  if (!dateStr) return '—'
  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  }).format(new Date(dateStr))
}

/**
 * Format large numbers with compact notation.
 */
export function formatCompact(num: number): string {
  if (num >= 1_00_00_000) return `₹${(num / 1_00_00_000).toFixed(1)}Cr`
  if (num >= 1_00_000) return `₹${(num / 1_00_000).toFixed(1)}L`
  if (num >= 1_000) return `₹${(num / 1_000).toFixed(1)}K`
  return `₹${num.toFixed(0)}`
}

/**
 * Truncate a string to a max length with ellipsis.
 */
export function truncate(str: string, maxLen: number = 40): string {
  if (!str) return ''
  return str.length > maxLen ? str.slice(0, maxLen) + '…' : str
}

/**
 * Get user-friendly error message from an Axios error.
 */
export function getErrorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'response' in error) {
    const axiosError = error as { response?: { data?: { detail?: string }; status?: number } }
    const detail = axiosError.response?.data?.detail
    if (detail) return typeof detail === 'string' ? detail : JSON.stringify(detail)
    const status = axiosError.response?.status
    if (status === 403) return 'You do not have permission to perform this action.'
    if (status === 404) return 'The requested resource was not found.'
    if (status === 500) return 'An internal server error occurred. Please try again later.'
  }
  if (error instanceof Error) return error.message
  return 'An unexpected error occurred.'
}
