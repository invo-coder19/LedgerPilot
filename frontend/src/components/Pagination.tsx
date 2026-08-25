import React from 'react'

interface PaginationProps {
  page: number
  pages: number
  total: number
  page_size: number
  onPageChange: (page: number) => void
}

const Pagination: React.FC<PaginationProps> = ({ page, pages, total, page_size, onPageChange }) => {
  if (pages <= 1) return null

  const from = (page - 1) * page_size + 1
  const to = Math.min(page * page_size, total)

  return (
    <div className="flex items-center justify-between px-4 py-3 border-t border-surface-border">
      <p className="text-sm text-slate-400">
        Showing <span className="text-slate-200 font-medium">{from}–{to}</span> of{' '}
        <span className="text-slate-200 font-medium">{total}</span> results
      </p>
      <div className="flex items-center gap-1">
        <button
          id="pagination-prev"
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="btn-secondary px-3 py-1.5 text-xs disabled:opacity-40"
        >
          ← Prev
        </button>
        {Array.from({ length: Math.min(pages, 7) }, (_, i) => {
          const pageNum = i + 1
          return (
            <button
              key={pageNum}
              id={`pagination-page-${pageNum}`}
              onClick={() => onPageChange(pageNum)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors duration-100 ${
                page === pageNum
                  ? 'bg-brand-500 text-white'
                  : 'text-slate-400 hover:bg-surface-hover hover:text-slate-200'
              }`}
            >
              {pageNum}
            </button>
          )
        })}
        <button
          id="pagination-next"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= pages}
          className="btn-secondary px-3 py-1.5 text-xs disabled:opacity-40"
        >
          Next →
        </button>
      </div>
    </div>
  )
}

export default Pagination
