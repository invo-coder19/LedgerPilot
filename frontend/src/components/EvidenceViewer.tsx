import React, { useState, useCallback } from 'react'
import type { EvidenceDocument } from '../types'

interface EvidenceViewerProps {
  title: string
  items: EvidenceDocument[]
  badgeColor?: string
  defaultExpanded?: boolean
}

const SOURCE_TYPE_ICONS: Record<string, string> = {
  TRANSACTION: '💳',
  SETTLEMENT: '🏦',
  INVOICE: '📄',
  BANK_TRANSACTION: '🏧',
  EXCEPTION: '⚠️',
  FINANCE_RULE: '📋',
  HISTORICAL_CASE: '📁',
}

const TRUST_COLORS: Record<string, string> = {
  PRIMARY: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10',
  SECONDARY: 'text-blue-400 border-blue-500/30 bg-blue-500/10',
  REFERENCE: 'text-violet-400 border-violet-500/30 bg-violet-500/10',
  HISTORICAL: 'text-amber-400 border-amber-500/30 bg-amber-500/10',
}

function EvidenceItem({ doc }: { doc: EvidenceDocument }) {
  const [expanded, setExpanded] = useState(false)
  const icon = SOURCE_TYPE_ICONS[doc.source_type] ?? '🔍'
  const trustColor = TRUST_COLORS[doc.trust_level] ?? TRUST_COLORS.SECONDARY
  const score = doc.similarity_score != null ? (doc.similarity_score * 100).toFixed(0) : null

  return (
    <div className="border border-surface-border rounded-lg overflow-hidden transition-all">
      {/* Header row */}
      <button
        id={`evidence-item-${doc.id}`}
        onClick={() => setExpanded(e => !e)}
        className="w-full flex items-center gap-3 p-3 text-left hover:bg-white/5 transition-colors"
      >
        <span className="text-base shrink-0">{icon}</span>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-slate-300 truncate">{doc.title}</p>
          {doc.source_id && (
            <p className="text-[11px] font-mono text-slate-500 truncate">{doc.source_id}</p>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {score && (
            <span className="text-[10px] text-slate-500">
              {score}% match
            </span>
          )}
          <span className={`text-[10px] border rounded px-1.5 py-0.5 font-medium ${trustColor}`}>
            {doc.trust_level}
          </span>
          <svg
            className={`w-3.5 h-3.5 text-slate-500 transition-transform ${expanded ? 'rotate-180' : ''}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="border-t border-surface-border px-3 pb-3 pt-2">
          <pre className="text-[11px] text-slate-400 whitespace-pre-wrap font-mono leading-relaxed overflow-auto max-h-56">
            {doc.content}
          </pre>
          {doc.metadata && Object.keys(doc.metadata).length > 0 && (
            <div className="mt-2 pt-2 border-t border-surface-border/50">
              <p className="text-[10px] text-slate-600 mb-1">Metadata</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(doc.metadata)
                  .filter(([, v]) => v != null && v !== false)
                  .slice(0, 6)
                  .map(([k, v]) => (
                    <span key={k} className="text-[10px] text-slate-500 font-mono bg-surface rounded px-1.5 py-0.5">
                      {k}: {String(v)}
                    </span>
                  ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const EvidenceViewer: React.FC<EvidenceViewerProps> = ({
  title,
  items,
  badgeColor = 'bg-slate-500/10 text-slate-400 border-slate-500/20',
  defaultExpanded = false,
}) => {
  const [open, setOpen] = useState(defaultExpanded)

  if (items.length === 0) return null

  return (
    <div className="rounded-xl border border-surface-border overflow-hidden">
      <button
        id={`evidence-section-${title.replace(/\s+/g, '-').toLowerCase()}`}
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-slate-300">{title}</span>
          <span className={`text-[11px] border rounded-full px-2 py-0.5 font-medium ${badgeColor}`}>
            {items.length}
          </span>
        </div>
        <svg
          className={`w-4 h-4 text-slate-500 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="px-3 pb-3 space-y-2 border-t border-surface-border">
          {items.map(doc => (
            <EvidenceItem key={doc.id} doc={doc} />
          ))}
        </div>
      )}
    </div>
  )
}

export default EvidenceViewer
