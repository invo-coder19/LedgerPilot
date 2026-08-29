import React from 'react'
import type { InvestigationStep } from '../types'

interface Props {
  steps: InvestigationStep[]
  durationMs?: number | null
}

const STEP_ICONS: Record<string, string> = {
  load_exception:          '📋',
  load_intelligence:       '🧠',
  plan_investigation:      '🗺️',
  retrieve_evidence:       '🔍',
  analyze_records:         '📊',
  check_ml_signals:        '🤖',
  check_finance_rules:     '📜',
  compare_historical_cases:'🕰️',
  determine_root_cause:    '🎯',
  validate_decision:       '✅',
  calculate_confidence:    '📐',
  generate_explanation:    '💬',
}

const STEP_LABELS: Record<string, string> = {
  load_exception:          'Loaded Exception',
  load_intelligence:       'Loaded ML Intelligence',
  plan_investigation:      'Planned Investigation',
  retrieve_evidence:       'Retrieved Evidence',
  analyze_records:         'Analyzed Records',
  check_ml_signals:        'Checked ML Signals',
  check_finance_rules:     'Checked Finance Rules',
  compare_historical_cases:'Compared Historical Cases',
  determine_root_cause:    'Determined Root Cause',
  validate_decision:       'Validated Decision',
  calculate_confidence:    'Calculated Confidence',
  generate_explanation:    'Generated Explanation',
}

export default function InvestigationTimeline({ steps, durationMs }: Props) {
  if (!steps.length) return null

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Investigation Timeline</h4>
        {durationMs && (
          <span className="text-xs text-slate-500">{(durationMs / 1000).toFixed(1)}s total</span>
        )}
      </div>

      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-4 top-0 bottom-0 w-px bg-violet-500/20" />

        <div className="space-y-2">
          {steps.map((step, idx) => {
            const icon = STEP_ICONS[step.step_name] || '⚙️'
            const label = STEP_LABELS[step.step_name] || step.step_name.replace(/_/g, ' ')
            const isLast = idx === steps.length - 1

            return (
              <div key={step.id} className="relative flex gap-3 pl-1">
                {/* Node */}
                <div className="relative z-10 flex-shrink-0 w-8 h-8 rounded-full bg-slate-800 border border-violet-500/30 flex items-center justify-center text-sm">
                  {icon}
                </div>

                {/* Content */}
                <div className={`flex-1 min-w-0 pb-2 ${isLast ? '' : ''}`}>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-medium text-slate-200">{label}</span>
                    {step.tool_name && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-slate-700 text-slate-400 font-mono">
                        {step.tool_name}
                      </span>
                    )}
                    {step.duration_ms != null && (
                      <span className="text-xs text-slate-500 ml-auto">{step.duration_ms}ms</span>
                    )}
                  </div>
                  {step.output_summary && (
                    <p className="text-xs text-slate-500 mt-0.5 truncate" title={step.output_summary}>
                      {step.output_summary}
                    </p>
                  )}
                </div>
              </div>
            )
          })}

          {/* End node */}
          <div className="relative flex gap-3 pl-1">
            <div className="relative z-10 flex-shrink-0 w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-sm">
              ✓
            </div>
            <div className="flex items-center">
              <span className="text-sm font-medium text-emerald-400">Investigation Complete</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
