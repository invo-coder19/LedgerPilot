import React, { useState } from 'react'
import InvestigationTimeline from './InvestigationTimeline'
import { investigationService } from '../services/investigationService'
import type { StartInvestigationResponse, InvestigationStep } from '../types'

interface Props {
  exceptionId: string
}

const BAND_COLORS = {
  HIGH:   'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
  MEDIUM: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
  LOW:    'text-red-400 bg-red-500/10 border-red-500/30',
}

const ROOT_CAUSE_LABELS: Record<string, string> = {
  FEE_VARIANCE:       'Fee Variance',
  AMOUNT_MISMATCH:    'Amount Mismatch',
  DUPLICATE:          'Duplicate',
  MISSING_INVOICE:    'Missing Invoice',
  MISSING_SETTLEMENT: 'Missing Settlement',
  REFUND_MISMATCH:    'Refund Mismatch',
  DATE_MISMATCH:      'Date Mismatch',
  UNKNOWN:            'Unknown / Insufficient Evidence',
}

function ConfidenceGauge({ value, band }: { value: number; band: string }) {
  const pct = Math.round(value * 100)
  const color = band === 'HIGH' ? '#10b981' : band === 'MEDIUM' ? '#f59e0b' : '#ef4444'
  const circumference = 2 * Math.PI * 36
  const strokeDash = (pct / 100) * circumference

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-20 h-20">
        <svg viewBox="0 0 80 80" className="rotate-[-90deg]">
          <circle cx="40" cy="40" r="36" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="7" />
          <circle
            cx="40" cy="40" r="36" fill="none"
            stroke={color} strokeWidth="7"
            strokeDasharray={`${strokeDash} ${circumference}`}
            strokeLinecap="round"
            style={{ transition: 'stroke-dasharray 0.8s ease' }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-lg font-bold" style={{ color }}>{pct}%</span>
        </div>
      </div>
      <span className={`mt-1 text-xs font-semibold px-2 py-0.5 rounded-full border ${BAND_COLORS[band as keyof typeof BAND_COLORS] || BAND_COLORS.LOW}`}>
        {band}
      </span>
    </div>
  )
}

export default function AIInvestigatorPanel({ exceptionId }: Props) {
  const [status, setStatus] = useState<'idle' | 'loading' | 'done' | 'error'>('idle')
  const [result, setResult] = useState<StartInvestigationResponse | null>(null)
  const [steps, setSteps] = useState<InvestigationStep[]>([])
  const [error, setError] = useState<string | null>(null)
  const [showTimeline, setShowTimeline] = useState(false)

  const handleInvestigate = async () => {
    setStatus('loading')
    setError(null)
    try {
      const res = await investigationService.investigate(exceptionId)
      setResult(res)
      setStatus(res.status === 'COMPLETED' ? 'done' : 'error')
      if (res.error) setError(res.error)

      // Load steps
      if (res.investigation_id) {
        try {
          const s = await investigationService.getSteps(res.investigation_id)
          setSteps(s)
        } catch { /* steps are optional */ }
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Investigation failed')
      setStatus('error')
    }
  }

  const r = result?.result

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg">🤖</span>
          <div>
            <h3 className="text-sm font-semibold text-slate-200">AI Finance Investigator</h3>
            <p className="text-xs text-slate-500">LangGraph · Powered by Gemini</p>
          </div>
        </div>
        {status === 'idle' && (
          <button
            id={`investigate-btn-${exceptionId}`}
            onClick={handleInvestigate}
            className="px-4 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium transition-all duration-200 flex items-center gap-2 shadow-lg shadow-violet-500/20"
          >
            <span>🔍</span>
            Investigate with AI
          </button>
        )}
        {status === 'done' && (
          <button
            onClick={handleInvestigate}
            className="px-3 py-1.5 rounded-lg border border-slate-600 text-slate-400 hover:text-slate-200 text-xs transition-colors"
          >
            Re-investigate
          </button>
        )}
      </div>

      {/* Loading state */}
      {status === 'loading' && (
        <div className="rounded-xl border border-violet-500/20 bg-violet-500/5 p-6 flex flex-col items-center gap-3">
          <div className="flex items-center gap-3">
            <div className="w-5 h-5 border-2 border-violet-400 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm text-violet-300 font-medium">AI Investigation in progress…</span>
          </div>
          <p className="text-xs text-slate-500 text-center">
            Loading exception → Planning → Retrieving evidence → Analyzing → Determining root cause
          </p>
          <div className="flex gap-1 mt-1">
            {Array.from({ length: 12 }).map((_, i) => (
              <div
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-violet-500/50 animate-pulse"
                style={{ animationDelay: `${i * 100}ms` }}
              />
            ))}
          </div>
        </div>
      )}

      {/* Error state */}
      {status === 'error' && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/5 p-4">
          <div className="flex items-start gap-3">
            <span className="text-red-400 text-lg">⚠️</span>
            <div>
              <p className="text-sm font-medium text-red-300">Investigation failed</p>
              <p className="text-xs text-slate-500 mt-1">
                {error || 'AI investigation temporarily unavailable. Deterministic and ML analysis remains available.'}
              </p>
              <button
                onClick={handleInvestigate}
                className="mt-2 text-xs text-violet-400 hover:text-violet-300 underline"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Result */}
      {status === 'done' && r && (
        <div className="space-y-4 animate-fade-in">
          {/* Human review alert */}
          {r.requires_human_review && (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-3 flex items-start gap-3">
              <span className="text-amber-400 text-lg mt-0.5">👤</span>
              <div>
                <p className="text-sm font-semibold text-amber-300">Human Review Required</p>
                {r.contradiction_detected && (
                  <p className="text-xs text-slate-500 mt-0.5">Conflicting evidence detected — confidence capped to ensure transparency.</p>
                )}
              </div>
            </div>
          )}

          {/* Root cause + confidence */}
          <div className="rounded-xl border border-slate-700/50 bg-slate-800/40 p-4 flex items-center gap-6">
            <ConfidenceGauge value={r.confidence} band={r.confidence_band} />
            <div className="flex-1 min-w-0">
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Root Cause</p>
              <p className="text-base font-bold text-slate-100">
                {ROOT_CAUSE_LABELS[r.root_cause] || r.root_cause}
              </p>
              <p className="text-xs text-slate-500 mt-0.5">{r.root_cause}</p>
            </div>
          </div>

          {/* Conclusion */}
          {r.conclusion && (
            <div className="rounded-xl border border-slate-700/40 bg-slate-800/30 p-4">
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Conclusion</h4>
              <p className="text-sm text-slate-300 leading-relaxed">{r.conclusion}</p>
            </div>
          )}

          {/* Observed facts */}
          {r.observed_facts?.length > 0 && (
            <div className="rounded-xl border border-slate-700/40 bg-slate-800/30 p-4">
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">📌 Observed Facts</h4>
              <ul className="space-y-1">
                {r.observed_facts.map((f, i) => (
                  <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                    <span className="text-emerald-400 mt-0.5 flex-shrink-0">●</span>
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Inferences */}
          {r.inferences?.length > 0 && (
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">💡 Inferences <span className="normal-case font-normal text-slate-500">(reasoned, not confirmed)</span></h4>
              <ul className="space-y-1">
                {r.inferences.map((f, i) => (
                  <li key={i} className="text-sm text-amber-200/80 flex items-start gap-2">
                    <span className="text-amber-400 mt-0.5 flex-shrink-0">~</span>
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Evidence citations */}
          {r.evidence_ids?.length > 0 && (
            <div className="rounded-xl border border-slate-700/40 bg-slate-800/30 p-4">
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">🔗 Evidence Cited</h4>
              <div className="flex flex-wrap gap-2">
                {r.evidence_ids.map((id, i) => (
                  <span
                    key={i}
                    className="px-2 py-1 rounded-lg bg-violet-500/10 border border-violet-500/20 text-xs text-violet-300 font-mono cursor-pointer hover:bg-violet-500/20 transition-colors"
                    title={id}
                  >
                    {id.length > 20 ? id.slice(0, 20) + '…' : id}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Recommendation */}
          {r.recommendation && (
            <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">📋 Recommendation</h4>
              <p className="text-sm text-blue-200/90 leading-relaxed">{r.recommendation}</p>
              {r.next_steps?.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {r.next_steps.map((s, i) => (
                    <li key={i} className="text-xs text-slate-400 flex items-start gap-2">
                      <span className="text-blue-400">{i + 1}.</span>
                      {s}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* Uncertainties */}
          {r.uncertainties?.length > 0 && (
            <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4">
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">⚠️ Uncertainties</h4>
              <ul className="space-y-1">
                {r.uncertainties.map((u, i) => (
                  <li key={i} className="text-xs text-red-300/80 flex items-start gap-2">
                    <span className="text-red-400 mt-0.5">!</span>
                    {u}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Timeline toggle */}
          {steps.length > 0 && (
            <div className="rounded-xl border border-slate-700/40 bg-slate-800/30 p-4">
              <button
                onClick={() => setShowTimeline(v => !v)}
                className="flex items-center gap-2 w-full text-left"
              >
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex-1">
                  🕐 Investigation Timeline
                </h4>
                <span className="text-xs text-slate-500">{showTimeline ? '▲ Hide' : '▼ Show'}</span>
              </button>
              {showTimeline && (
                <div className="mt-3">
                  <InvestigationTimeline steps={steps} />
                </div>
              )}
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between text-xs text-slate-600">
            <span>Investigation ID: {result?.investigation_id?.slice(0, 8)}…</span>
            <span className="italic">Read-only · No financial actions taken</span>
          </div>
        </div>
      )}
    </div>
  )
}
