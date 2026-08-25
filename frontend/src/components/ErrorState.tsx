import React from 'react'

interface ErrorStateProps {
  message: string
  onRetry?: () => void
}

const ErrorState: React.FC<ErrorStateProps> = ({ message, onRetry }) => (
  <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
    <div className="mb-4 p-4 rounded-full bg-red-500/10 text-red-400">
      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
          d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
      </svg>
    </div>
    <h3 className="text-base font-semibold text-slate-300 mb-1">Something went wrong</h3>
    <p className="text-sm text-slate-500 max-w-sm mb-4">{message}</p>
    {onRetry && (
      <button id="error-retry-btn" onClick={onRetry} className="btn-secondary text-sm">
        Try again
      </button>
    )}
  </div>
)

export default ErrorState
