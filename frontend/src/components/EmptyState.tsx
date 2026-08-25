import React from 'react'

interface EmptyStateProps {
  title: string
  description: string
  icon?: React.ReactNode
}

const EmptyState: React.FC<EmptyStateProps> = ({ title, description, icon }) => (
  <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
    {icon && (
      <div className="mb-4 p-4 rounded-full bg-surface-card text-slate-500">
        {icon}
      </div>
    )}
    <h3 className="text-base font-semibold text-slate-300 mb-1">{title}</h3>
    <p className="text-sm text-slate-500 max-w-sm">{description}</p>
  </div>
)

export default EmptyState
