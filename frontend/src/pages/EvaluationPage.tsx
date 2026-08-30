import React, { useEffect, useState } from 'react'
import { evaluationService } from '../services/evaluationService'
import type { EvaluationSummary } from '../types'

const MetricCard: React.FC<{
  label: string
  value: string
  sub?: string
  color?: string
  icon?: string
}> = ({ label, value, sub, color = 'text-brand-400', icon }) => (
  <div className="card-base p-5">
    <div className="flex items-start justify-between mb-2">
      <span className="text-xs text-slate-400 uppercase tracking-wide">{label}</span>
      {icon && <span className="text-lg">{icon}</span>}
    </div>
    <div className={`text-2xl font-bold ${color}`}>{value}</div>
    {sub && <div className="text-xs text-slate-500 mt-1">{sub}</div>}
  </div>
)

const SectionHeader: React.FC<{ title: string; badge?: string }> = ({ title, badge }) => (
  <div className="flex items-center gap-3 mb-4">
    <h2 className="text-base font-semibold text-slate-200">{title}</h2>
    {badge && (
      <span className="text-xs bg-brand-500/20 text-brand-300 px-2 py-0.5 rounded-full">{badge}</span>
    )}
  </div>
)

const pct = (v: number) => `${(v * 100).toFixed(1)}%`
const inr = (v: number) => {
  if (v >= 1_00_000) return `₹${(v / 1_00_000).toFixed(2)}L`
  return `₹${v.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}

const TRUST_PROPERTIES = [
  'Evidence-backed AI decisions — every recommendation cites source records',
  'Confidence gating — autonomy blocked below configurable threshold',
  'Deterministic policy engine — LLM cannot override financial rules',
  'Human approval workflow for medium and high-risk decisions',
  'Kill switch — instant halt of all autonomous actions',
  'Idempotency — duplicate submissions safely rejected',
  'Complete audit trail — every action linked to user, reason, and evidence',
  'Failure-safe defaults — missing data → human review, never open execution',
  'Reproducible benchmarks — seeded synthetic data, git-commit tagged runs',
]

const EvaluationPage: React.FC = () => {
  const [summary, setSummary] = useState<EvaluationSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    evaluationService.getSummary()
      .then(setSummary)
      .catch(() => setError('No evaluation data available. Run a benchmark first.'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="page-container">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="page-title">Evaluation & Benchmark</h1>
          <p className="text-sm text-slate-400 mt-1">
            Ground-truth accuracy metrics on synthetic benchmark data
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-amber-400 bg-amber-400/10 border border-amber-400/20 rounded-lg px-3 py-2">
          <span>⚠</span>
          <span>Synthetic benchmark data — No real money</span>
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full" />
        </div>
      )}

      {error && !loading && (
        <div className="card-base p-8 text-center">
          <div className="text-4xl mb-3">📊</div>
          <h3 className="text-slate-200 font-medium mb-2">No Evaluation Data</h3>
          <p className="text-slate-400 text-sm max-w-md mx-auto">{error}</p>
          <p className="text-slate-500 text-xs mt-3">
            Run: <code className="bg-surface-border px-1 rounded">python -m app.evaluation generate_dataset --records 1000 --seed 42</code>
          </p>
        </div>
      )}

      {summary && !loading && summary.status !== 'NO_DATA' && (
        <>
          {/* Run Info */}
          <div className="flex items-center gap-3 text-xs text-slate-500 mb-6">
            <span>Run: <code className="text-slate-300">{summary.run_id?.slice(0, 8)}...</code></span>
            <span>•</span>
            <span>{summary.records_tested.toLocaleString()} cases tested</span>
            <span>•</span>
            <span>Dataset {summary.dataset_version}</span>
          </div>

          {/* Critical Metrics */}
          <SectionHeader title="Key Performance Metrics" badge="Competition KPIs" />
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <MetricCard icon="🎯" label="Reconciliation Accuracy" value={pct(summary.reconciliation_accuracy)}
              color={summary.reconciliation_accuracy >= 0.9 ? 'text-green-400' : 'text-amber-400'} />
            <MetricCard icon="🤖" label="ML F1 Score (Weighted)" value={pct(summary.ml_f1_weighted)}
              color={summary.ml_f1_weighted >= 0.8 ? 'text-green-400' : 'text-amber-400'} />
            <MetricCard icon="📎" label="Citation Correctness" value={pct(summary.citation_correctness)}
              color={summary.citation_correctness >= 0.9 ? 'text-green-400' : 'text-amber-400'}
              sub="Anti-hallucination score" />
            <MetricCard icon="⚙️" label="Auto-Resolution Precision" value={pct(summary.auto_resolution_precision)}
              color={summary.auto_resolution_precision >= 0.95 ? 'text-green-400' : 'text-amber-400'}
              sub="% correctly auto-resolved" />
          </div>

          {/* Reconciliation */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <div className="card-base p-5">
              <SectionHeader title="Reconciliation Engine" />
              <div className="space-y-3">
                {[
                  ['Exact Match Accuracy', pct(summary.reconciliation_accuracy)],
                  ['Match Rate', pct(summary.match_rate)],
                  ['Precision', pct(summary.reconciliation_precision)],
                  ['Recall', pct(summary.reconciliation_recall)],
                  ['False Positive Rate', pct(summary.false_positive_rate)],
                ].map(([label, val]) => (
                  <div key={label} className="flex items-center justify-between text-sm">
                    <span className="text-slate-400">{label}</span>
                    <span className="font-mono text-slate-200">{val}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="card-base p-5">
              <SectionHeader title="ML Exception Classification" />
              <div className="space-y-3">
                {[
                  ['Accuracy', pct(summary.ml_accuracy)],
                  ['F1 Macro', pct(summary.ml_f1_macro)],
                  ['F1 Weighted', pct(summary.ml_f1_weighted)],
                  ['Uncertainty Accuracy', pct(summary.uncertainty_accuracy)],
                ].map(([label, val]) => (
                  <div key={label} className="flex items-center justify-between text-sm">
                    <span className="text-slate-400">{label}</span>
                    <span className="font-mono text-slate-200">{val}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Controller + Financial */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <div className="card-base p-5">
              <SectionHeader title="Autonomous Controller" />
              <div className="space-y-3">
                {[
                  ['Decision Accuracy', pct(summary.decision_accuracy)],
                  ['Auto-Resolution Rate', pct(summary.auto_resolution_rate)],
                  ['Auto-Resolution Precision', pct(summary.auto_resolution_precision)],
                  ['Human Review Rate', pct(summary.human_review_rate)],
                  ['Escalation Rate', pct(summary.escalation_rate)],
                ].map(([label, val]) => (
                  <div key={label} className="flex items-center justify-between text-sm">
                    <span className="text-slate-400">{label}</span>
                    <span className="font-mono text-slate-200">{val}</span>
                  </div>
                ))}
                <div className="border-t border-surface-border pt-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-amber-400">Autonomous Error Rate</span>
                    <span className="font-mono text-amber-300 font-bold">{pct(summary.autonomous_error_rate)}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="card-base p-5">
              <SectionHeader title="Financial Impact" />
              <div className="space-y-3">
                {[
                  ['Amount Processed', inr(summary.amount_processed_inr)],
                  ['Amount Auto-Resolved', inr(summary.amount_auto_resolved_inr)],
                  ['Human Interventions Avoided', `${summary.human_interventions_avoided}`],
                ].map(([label, val]) => (
                  <div key={label} className="flex items-center justify-between text-sm">
                    <span className="text-slate-400">{label}</span>
                    <span className="font-mono text-green-300">{val}</span>
                  </div>
                ))}
                <div className="border-t border-surface-border pt-2 space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-red-400">False-Positive Cost</span>
                    <span className="font-mono text-red-300">{inr(summary.false_positive_cost_inr)}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-amber-400">False-Negative Cost</span>
                    <span className="font-mono text-amber-300">{inr(summary.false_negative_cost_inr)}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-red-400 font-medium">Financial Error Rate</span>
                    <span className="font-mono text-red-300 font-bold">{pct(summary.financial_error_rate)}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Trust Properties */}
          <div className="card-base p-5">
            <SectionHeader title="Why LedgerPilot Can Be Trusted" badge="Safety Properties" />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-2">
              {TRUST_PROPERTIES.map((prop, i) => (
                <div key={i} className="flex items-start gap-2 text-sm text-slate-300 py-1">
                  <span className="text-green-400 mt-0.5 flex-shrink-0">✓</span>
                  <span>{prop}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default EvaluationPage
