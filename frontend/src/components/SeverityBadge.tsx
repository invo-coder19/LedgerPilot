import React from 'react'
import type { ExceptionSeverity } from '../types'

const SEVERITY_STYLES: Record<ExceptionSeverity, string> = {
  LOW:      'bg-slate-500/10 text-slate-400 border border-slate-500/20',
  MEDIUM:   'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20',
  HIGH:     'bg-orange-500/10 text-orange-400 border border-orange-500/20',
  CRITICAL: 'bg-red-500/10 text-red-400 border border-red-500/20',
}

interface SeverityBadgeProps {
  severity: ExceptionSeverity
}

const SeverityBadge: React.FC<SeverityBadgeProps> = ({ severity }) => (
  <span className={`badge ${SEVERITY_STYLES[severity]}`}>
    {severity}
  </span>
)

export default SeverityBadge
