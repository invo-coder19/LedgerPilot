import React from 'react'

interface LoadingSkeletonProps {
  rows?: number
  cols?: number
}

const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({ rows = 5, cols = 6 }) => (
  <div className="space-y-2 p-4">
    {Array.from({ length: rows }).map((_, i) => (
      <div key={i} className="flex gap-4">
        {Array.from({ length: cols }).map((_, j) => (
          <div
            key={j}
            className="skeleton h-8 rounded"
            style={{ flex: j === 0 ? '2' : '1' }}
          />
        ))}
      </div>
    ))}
  </div>
)

export const KPISkeletons: React.FC = () => (
  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
    {Array.from({ length: 6 }).map((_, i) => (
      <div key={i} className="card p-5 flex flex-col gap-4">
        <div className="skeleton h-8 w-8 rounded-lg" />
        <div className="skeleton h-7 w-24 rounded" />
        <div className="skeleton h-4 w-32 rounded" />
      </div>
    ))}
  </div>
)

export default LoadingSkeleton
