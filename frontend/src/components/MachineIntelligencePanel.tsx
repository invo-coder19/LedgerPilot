import React, { useState, useCallback } from 'react'
import type { IntelligenceContext, MLAnalysisResponse } from '../types'
import { intelligenceService } from '../services/intelligenceService'
import { getErrorMessage } from '../utils/format'
import EvidenceViewer from './EvidenceViewer'

interface MachineIntelligencePanelProps {
  exceptionId: string
  /** Pre-loaded context from GET /intelligence-context, or null if not loaded yet */
  initialContext?: IntelligenceContext | null
}

// ── Sub-components ────────────────────────────────────────────────────────────

function ConfidenceBar({ value, color }: { value: number; color: string }) {
  const pct = Math.round(value * 100)
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-slate-800 rounded-full h-1.5 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-mono text-slate-400 w-10 text-right">{pct}%</span>
    </div>
  )
}

function AnomalyGauge({ score, isAnomaly }: { score: number; isAnomaly: boolean }) {
  const pct = Math.round(score * 100)
  const color = isAnomaly
    ? 'bg-gradient-to-r from-amber-500 to-red-500'
    : 'bg-gradient-to-r from-emerald-600 to-emerald-400'
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-400">Anomaly Score</span>
        <span className={`font-mono font-bold ${isAnomaly ? 'text-red-400' : 'text-emerald-400'}`}>
          {pct}%
        </span>
      </div>
      <div className="bg-slate-800 rounded-full h-2.5 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex items-center gap-1.5 mt-1">
        <span className={`inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full ${
          isAnomaly
            ? 'bg-red-500/10 text-red-400 border border-red-500/20'
            : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
        }`}>
          {isAnomaly ? '⚠ Anomalous' : '✓ Normal pattern'}
        </span>
      </div>
    </div>
  )
}

function ClassifierResult({ prediction }: {
  prediction: NonNullable<IntelligenceContext['ml_prediction']>
}) {
  const [showAlt, setShowAlt] = useState(false)
  const confColor =
    prediction.confidence > 0.75 ? 'bg-emerald-500' :
    prediction.confidence > 0.5 ? 'bg-amber-500' : 'bg-red-400'

  return (
    <div className="space-y-3">
      <div>
        <p className="label mb-1">Predicted Exception Type</p>
        <p className="text-sm font-semibold text-slate-100 tracking-wide">
          {prediction.predicted_type.replace(/_/g, ' ')}
        </p>
      </div>
      <div className="space-y-1">
        <p className="label">Confidence</p>
        <ConfidenceBar value={prediction.confidence} color={confColor} />
      </div>
      {prediction.top_alternatives?.length > 0 && (
        <div>
          <button
            onClick={() => setShowAlt(s => !s)}
            className="text-[11px] text-slate-500 hover:text-slate-400 transition-colors"
          >
            {showAlt ? '▲ Hide' : '▼ Show'} {prediction.top_alternatives.length} alternatives
          </button>
          {showAlt && (
            <div className="mt-2 space-y-1.5">
              {prediction.top_alternatives.map(alt => (
                <div key={alt.label}>
                  <div className="flex justify-between text-[11px] mb-0.5">
                    <span className="text-slate-400">{alt.label.replace(/_/g, ' ')}</span>
                  </div>
                  <ConfidenceBar value={alt.confidence} color="bg-slate-500" />
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      <p className="text-[10px] text-slate-600 italic">
        v{prediction.model_version} · {new Date(prediction.created_at).toLocaleString()}
      </p>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

const MachineIntelligencePanel: React.FC<MachineIntelligencePanelProps> = ({
  exceptionId,
  initialContext,
}) => {
  const [context, setContext] = useState<IntelligenceContext | null>(initialContext ?? null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')
  const [runResult, setRunResult] = useState<MLAnalysisResponse | null>(null)

  const handleRunML = useCallback(async () => {
    setRunning(true)
    setError('')
    try {
      const result = await intelligenceService.runMlAnalysis(exceptionId)
      setRunResult(result)
      // Reload context after running ML
      const ctx = await intelligenceService.getIntelligenceContext(exceptionId)
      setContext(ctx)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setRunning(false)
    }
  }, [exceptionId])

  const handleLoadContext = useCallback(async () => {
    setRunning(true)
    setError('')
    try {
      const ctx = await intelligenceService.getIntelligenceContext(exceptionId)
      setContext(ctx)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setRunning(false)
    }
  }, [exceptionId])

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-violet-500/10 border border-violet-500/20 flex items-center justify-center">
            <svg className="w-4 h-4 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.347.347a3.5 3.5 0 01-4.95 0l-.346-.346z" />
            </svg>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-100">Machine Intelligence</h3>
            <p className="text-[11px] text-slate-500">Phase 3A — Classification & Evidence</p>
          </div>
        </div>
        <div className="flex gap-2">
          {!context && (
            <button
              id="load-intelligence-btn"
              onClick={handleLoadContext}
              disabled={running}
              className="btn-secondary text-xs disabled:opacity-50"
            >
              {running ? 'Loading…' : 'Load Context'}
            </button>
          )}
          <button
            id="run-ml-analysis-btn"
            onClick={handleRunML}
            disabled={running}
            className="btn-primary text-xs disabled:opacity-50"
          >
            {running ? (
              <span className="flex items-center gap-1.5">
                <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                </svg>
                Running…
              </span>
            ) : '⚡ Run ML Analysis'}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
          {error}
        </div>
      )}

      {/* Models not available notice */}
      {context && !context.models_available && (
        <div className="px-4 py-3 rounded-xl bg-amber-500/5 border border-amber-500/20">
          <p className="text-xs text-amber-400 font-medium">⚠ ML Models Not Trained</p>
          <p className="text-[11px] text-slate-500 mt-1">
            Run <code className="bg-slate-800 px-1 rounded font-mono">python -m app.ml.training</code> to
            train the classifier and anomaly detector.
          </p>
        </div>
      )}

      {/* No context loaded */}
      {!context && !running && (
        <div className="px-4 py-8 rounded-xl border border-dashed border-surface-border text-center">
          <p className="text-sm text-slate-500">Click <strong className="text-slate-400">Load Context</strong> to load intelligence data, or <strong className="text-slate-400">Run ML Analysis</strong> to generate new predictions.</p>
        </div>
      )}

      {context && (
        <>
          {/* ML Classifier */}
          {context.ml_prediction ? (
            <div className="card p-4 space-y-3">
              <p className="text-xs font-semibold text-violet-400 uppercase tracking-wider">
                Exception Classifier
              </p>
              <ClassifierResult prediction={context.ml_prediction} />
            </div>
          ) : context.models_available && (
            <div className="card p-4 text-center">
              <p className="text-xs text-slate-500">No classification result yet. Click Run ML Analysis.</p>
            </div>
          )}

          {/* Anomaly Detector */}
          {context.anomaly_analysis && (
            <div className="card p-4 space-y-2">
              <p className="text-xs font-semibold text-violet-400 uppercase tracking-wider mb-2">
                Anomaly Detection
              </p>
              <AnomalyGauge
                score={context.anomaly_analysis.anomaly_score}
                isAnomaly={context.anomaly_analysis.is_anomaly}
              />
              <p className="text-[10px] text-slate-600 italic">
                v{context.anomaly_analysis.model_version} · IsolationForest
              </p>
            </div>
          )}

          {/* ML Agreement */}
          {context.ml_agreement && (
            <div className={`card p-3 flex items-start gap-3 ${
              context.ml_agreement.agree
                ? 'border-emerald-500/20 bg-emerald-500/5'
                : 'border-amber-500/20 bg-amber-500/5'
            }`}>
              <span className="text-lg shrink-0">{context.ml_agreement.agree ? '✅' : '⚠️'}</span>
              <div>
                <p className="text-xs font-medium text-slate-300 mb-0.5">Classification Agreement</p>
                <p className="text-[11px] text-slate-400">{context.ml_agreement.note}</p>
              </div>
            </div>
          )}

          {/* Evidence Summary */}
          {context.evidence_counts.total > 0 && (
            <div className="card p-4">
              <div className="flex items-center justify-between mb-3">
                <p className="text-xs font-semibold text-violet-400 uppercase tracking-wider">
                  Evidence ({context.evidence_counts.total} records)
                </p>
                <span className="text-[11px] text-slate-500">Phase 3B ready: {context.phase_3b_ready ? '✓' : '…'}</span>
              </div>
              <div className="grid grid-cols-3 gap-2 mb-4">
                {[
                  { label: 'Transactions', count: context.evidence_counts.transactions, color: 'text-blue-400' },
                  { label: 'Settlements', count: context.evidence_counts.settlements, color: 'text-emerald-400' },
                  { label: 'Invoices', count: context.evidence_counts.invoices, color: 'text-violet-400' },
                  { label: 'Bank', count: context.evidence_counts.bank_transactions, color: 'text-slate-400' },
                  { label: 'Rules', count: context.evidence_counts.finance_rules, color: 'text-amber-400' },
                  { label: 'Cases', count: context.evidence_counts.historical_cases, color: 'text-rose-400' },
                ].map(({ label, count, color }) => (
                  <div key={label} className="text-center p-2 rounded-lg bg-surface">
                    <p className={`text-base font-bold ${color}`}>{count}</p>
                    <p className="text-[10px] text-slate-500">{label}</p>
                  </div>
                ))}
              </div>

              {/* Evidence sections */}
              <div className="space-y-2">
                <EvidenceViewer
                  title="Transaction Records"
                  items={context.transaction_evidence}
                  badgeColor="bg-blue-500/10 text-blue-400 border-blue-500/20"
                  defaultExpanded
                />
                <EvidenceViewer
                  title="Settlement Records"
                  items={context.settlement_evidence}
                  badgeColor="bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                />
                <EvidenceViewer
                  title="Invoice Records"
                  items={context.invoice_evidence}
                  badgeColor="bg-violet-500/10 text-violet-400 border-violet-500/20"
                />
                <EvidenceViewer
                  title="Bank Transactions"
                  items={context.bank_evidence}
                  badgeColor="bg-slate-500/10 text-slate-400 border-slate-500/20"
                />
                <EvidenceViewer
                  title="Finance Rules"
                  items={context.finance_rules}
                  badgeColor="bg-amber-500/10 text-amber-400 border-amber-500/20"
                />
                <EvidenceViewer
                  title="Similar Historical Cases"
                  items={context.historical_cases}
                  badgeColor="bg-rose-500/10 text-rose-400 border-rose-500/20"
                />
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default MachineIntelligencePanel
