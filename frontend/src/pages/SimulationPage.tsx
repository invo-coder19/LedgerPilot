import React, { useEffect, useState } from 'react'
import { simulationService } from '../services/simulationService'
import type { SimulationScenario, SimulationResult } from '../types'

const CATEGORY_COLORS: Record<string, string> = {
  data: 'text-blue-400 bg-blue-400/10 border-blue-400/20',
  ai: 'text-purple-400 bg-purple-400/10 border-purple-400/20',
  execution: 'text-orange-400 bg-orange-400/10 border-orange-400/20',
  infrastructure: 'text-slate-300 bg-slate-500/10 border-slate-500/20',
  safety: 'text-red-400 bg-red-400/10 border-red-400/20',
}

const CATEGORY_ICONS: Record<string, string> = {
  data: '🗂️',
  ai: '🤖',
  execution: '⚡',
  infrastructure: '🏗️',
  safety: '🛡️',
}

const ScenarioCard: React.FC<{
  scenario: SimulationScenario
  result: SimulationResult | null
  running: boolean
  onRun: () => void
}> = ({ scenario, result, running, onRun }) => {
  const catStyle = CATEGORY_COLORS[scenario.category] || 'text-slate-400 bg-slate-400/10 border-slate-400/20'

  return (
    <div className={`card-base p-5 transition-all ${result ? (result.passed ? 'border-green-400/20' : 'border-red-400/20') : ''}`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">{CATEGORY_ICONS[scenario.category] || '⚙️'}</span>
          <div>
            <div className="font-medium text-slate-200 text-sm">{scenario.name}</div>
            <span className={`text-xs border rounded px-1.5 py-0.5 ${catStyle}`}>{scenario.category}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {result && (
            <span className={`text-xs font-bold px-2 py-1 rounded-full ${result.passed ? 'text-green-400 bg-green-400/10' : 'text-red-400 bg-red-400/10'}`}>
              {result.passed ? '✓ PASS' : '✗ FAIL'}
            </span>
          )}
          <button
            id={`sim-run-${scenario.id}`}
            onClick={onRun}
            disabled={running}
            className="btn-primary text-xs px-3 py-1.5"
          >
            {running ? (
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" />
                Running
              </span>
            ) : 'Run'}
          </button>
        </div>
      </div>

      {/* Scenario description */}
      <div className="space-y-2 text-xs text-slate-400">
        <div>
          <span className="text-slate-500 uppercase tracking-wide">Failure: </span>
          {scenario.failure_injected}
        </div>
        <div>
          <span className="text-slate-500 uppercase tracking-wide">Expected: </span>
          {scenario.expected_outcome}
        </div>
        <div className="text-brand-400/80">
          <span className="text-slate-500 uppercase tracking-wide">Safety Property: </span>
          {scenario.safety_property}
        </div>
      </div>

      {/* Result */}
      {result && (
        <div className={`mt-4 border rounded-lg p-3 ${result.passed ? 'bg-green-400/5 border-green-400/10' : 'bg-red-400/5 border-red-400/10'}`}>
          <div className="text-xs font-medium mb-1" style={{ color: result.passed ? '#4ade80' : '#f87171' }}>
            Actual Behavior:
          </div>
          <div className="text-xs text-slate-300">{result.actual_behavior}</div>
          {result.evidence.length > 0 && (
            <div className="mt-2 space-y-0.5">
              {result.evidence.map((e, i) => (
                <div key={i} className="text-xs text-slate-500 flex items-start gap-1">
                  <span className="text-slate-600 mt-0.5">›</span>
                  <span>{e}</span>
                </div>
              ))}
            </div>
          )}
          {result.duration_ms > 0 && (
            <div className="text-xs text-slate-600 mt-2">{result.duration_ms}ms</div>
          )}
        </div>
      )}
    </div>
  )
}

const SimulationPage: React.FC = () => {
  const [scenarios, setScenarios] = useState<SimulationScenario[]>([])
  const [results, setResults] = useState<Record<string, SimulationResult>>({})
  const [running, setRunning] = useState<Record<string, boolean>>({})
  const [runningAll, setRunningAll] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    simulationService.listScenarios()
      .then(setScenarios)
      .finally(() => setLoading(false))
  }, [])

  const runScenario = async (id: string) => {
    setRunning(r => ({ ...r, [id]: true }))
    try {
      const result = await simulationService.runScenario(id)
      setResults(r => ({ ...r, [id]: result }))
    } catch {
      setResults(r => ({ ...r, [id]: {
        scenario_id: id,
        scenario_name: id,
        passed: false,
        initial_state: {},
        failure_injected: '',
        expected_behavior: '',
        actual_behavior: 'Simulation failed — ensure backend is running',
        evidence: [],
        duration_ms: 0,
        error: 'Request failed',
        timestamp: new Date().toISOString(),
        demo_disclaimer: '',
      }}))
    } finally {
      setRunning(r => ({ ...r, [id]: false }))
    }
  }

  const runAll = async () => {
    setRunningAll(true)
    try {
      const allResults = await simulationService.runAll()
      const mapped = Object.fromEntries(allResults.map(r => [r.scenario_id, r]))
      setResults(mapped)
    } finally {
      setRunningAll(false)
    }
  }

  const passCount = Object.values(results).filter(r => r.passed).length
  const failCount = Object.values(results).filter(r => !r.passed).length

  return (
    <div className="page-container">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h1 className="page-title">Failure Simulation</h1>
          <p className="text-sm text-slate-400 mt-1">
            9 controlled failure scenarios demonstrating safety properties
          </p>
        </div>
        <button
          id="run-all-simulations"
          onClick={runAll}
          disabled={runningAll || loading}
          className="btn-primary text-sm"
        >
          {runningAll ? 'Running all...' : '▶ Run All Scenarios'}
        </button>
      </div>

      {/* Disclaimer */}
      <div className="flex items-center gap-3 text-xs text-amber-400 bg-amber-400/10 border border-amber-400/20 rounded-lg px-4 py-3 mb-6">
        <span className="text-base">⚠</span>
        <div>
          <span className="font-bold">DEMO / SIMULATION MODE</span>
          <span className="text-amber-400/70 ml-2">— No real money movement — State restored after each test</span>
        </div>
      </div>

      {/* Summary bar */}
      {Object.keys(results).length > 0 && (
        <div className="flex items-center gap-4 mb-6 p-4 card-base">
          <span className="text-sm text-slate-400">Results:</span>
          <span className="text-sm text-green-400 font-semibold">{passCount} PASSED</span>
          {failCount > 0 && <span className="text-sm text-red-400 font-semibold">{failCount} FAILED</span>}
          <span className="text-sm text-slate-500">/ {scenarios.length} total</span>
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center h-40">
          <div className="animate-spin w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full" />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {scenarios.map(s => (
          <ScenarioCard
            key={s.id}
            scenario={s}
            result={results[s.id] || null}
            running={running[s.id] || runningAll}
            onRun={() => runScenario(s.id)}
          />
        ))}
      </div>
    </div>
  )
}

export default SimulationPage
