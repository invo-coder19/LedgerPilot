import React, { useEffect, useState, useCallback } from 'react'
import { healthService } from '../services/healthService'
import type { SystemHealth, ComponentHealth, HealthStatus } from '../types'

const statusColor: Record<HealthStatus | string, string> = {
  healthy: 'text-green-400',
  configured: 'text-green-400',
  degraded: 'text-amber-400',
  unavailable: 'text-amber-400',
  not_configured: 'text-slate-400',
  unhealthy: 'text-red-400',
}

const statusBg: Record<HealthStatus | string, string> = {
  healthy: 'bg-green-400',
  configured: 'bg-green-400',
  degraded: 'bg-amber-400',
  unavailable: 'bg-amber-400',
  not_configured: 'bg-slate-500',
  unhealthy: 'bg-red-400',
}

const statusLabel: Record<string, string> = {
  healthy: 'Healthy',
  configured: 'Configured',
  degraded: 'Degraded',
  unavailable: 'Unavailable',
  not_configured: 'Not Configured',
  unhealthy: 'Unhealthy',
}

const COMPONENT_ICONS: Record<string, string> = {
  api: '⚡',
  database: '🗄️',
  redis: '🔄',
  ml_models: '🤖',
  rag: '📚',
  llm_provider: '🧠',
}

const COMPONENT_DESCRIPTIONS: Record<string, string> = {
  api: 'FastAPI application server',
  database: 'PostgreSQL — transaction and exception storage',
  redis: 'Redis — Celery task broker and cache',
  ml_models: 'Scikit-learn + XGBoost exception classifier and anomaly detector',
  rag: 'Sentence-transformers evidence retrieval store',
  llm_provider: 'LLM for AI investigation (Gemini / OpenAI)',
}

const ComponentCard: React.FC<{ name: string; health: ComponentHealth }> = ({ name, health }) => {
  const status = health.status as string
  const icon = COMPONENT_ICONS[name] || '⚙️'
  const description = COMPONENT_DESCRIPTIONS[name] || name

  return (
    <div className="card-base p-5 flex items-start gap-4">
      <div className="text-2xl">{icon}</div>
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-medium text-slate-200 capitalize">{name.replace('_', ' ')}</span>
          <span className={`w-2 h-2 rounded-full ${statusBg[status] || 'bg-slate-500'}`} />
          <span className={`text-xs font-medium ${statusColor[status] || 'text-slate-400'}`}>
            {statusLabel[status] || status}
          </span>
        </div>
        <p className="text-xs text-slate-500 mb-2">{description}</p>
        {health.latency_ms !== undefined && (
          <div className="text-xs text-slate-400">Latency: {health.latency_ms}ms</div>
        )}
        {health.error && (
          <div className="text-xs text-red-400 bg-red-400/5 border border-red-400/10 rounded px-2 py-1 mt-1">
            {health.error}
          </div>
        )}
        {health.note && (
          <div className="text-xs text-amber-400/80 mt-1">{health.note}</div>
        )}
        {/* Extra details */}
        {name === 'ml_models' && health.classifier && (
          <div className="text-xs text-slate-500 mt-1">
            Classifier: {String(health.classifier)} · Anomaly: {String(health.anomaly_detector)}
          </div>
        )}
        {name === 'rag' && health.document_count !== undefined && (
          <div className="text-xs text-slate-500 mt-1">
            {health.document_count as number} evidence documents indexed
          </div>
        )}
        {name === 'llm_provider' && health.provider && (
          <div className="text-xs text-slate-500 mt-1">
            Provider: {String(health.provider)} · Model: {String(health.model || 'default')}
          </div>
        )}
      </div>
    </div>
  )
}

const SystemHealthPage: React.FC = () => {
  const [health, setHealth] = useState<SystemHealth | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null)

  const fetchHealth = useCallback(() => {
    setLoading(true)
    healthService.getDetailed()
      .then(data => {
        setHealth(data)
        setLastRefresh(new Date())
      })
      .catch(() => setHealth(null))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    fetchHealth()
    const interval = setInterval(fetchHealth, 30000) // Auto-refresh every 30s
    return () => clearInterval(interval)
  }, [fetchHealth])

  const overallColor = health?.overall === 'healthy' ? 'text-green-400 bg-green-400/10 border-green-400/20'
    : health?.overall === 'degraded' ? 'text-amber-400 bg-amber-400/10 border-amber-400/20'
    : 'text-red-400 bg-red-400/10 border-red-400/20'

  return (
    <div className="page-container">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="page-title">System Health</h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time status of all LedgerPilot components
          </p>
        </div>
        <div className="flex items-center gap-3">
          {lastRefresh && (
            <span className="text-xs text-slate-500">
              Updated {lastRefresh.toLocaleTimeString()}
            </span>
          )}
          <button
            onClick={fetchHealth}
            disabled={loading}
            className="btn-secondary text-xs px-3 py-1.5"
          >
            {loading ? '...' : '↺ Refresh'}
          </button>
        </div>
      </div>

      {/* Demo Banner */}
      <div className="flex items-center gap-3 text-xs text-amber-400 bg-amber-400/10 border border-amber-400/20 rounded-lg px-4 py-3 mb-6">
        <span className="text-base">⚠</span>
        <div>
          <span className="font-semibold">DEMO ENVIRONMENT</span>
          <span className="text-amber-400/70 ml-2">— Synthetic financial data only — No real money movement</span>
        </div>
      </div>

      {/* Overall status */}
      {health && (
        <div className={`flex items-center gap-3 border rounded-xl px-5 py-4 mb-6 ${overallColor}`}>
          <span className="text-xl">{health.overall === 'healthy' ? '✓' : health.overall === 'degraded' ? '⚠' : '✗'}</span>
          <div>
            <div className="font-semibold capitalize">{statusLabel[health.overall] || health.overall}</div>
            <div className="text-xs opacity-70">
              v{health.version} · {health.environment} · {health.demo_mode ? 'Demo Mode' : 'Production Mode'}
            </div>
          </div>
        </div>
      )}

      {/* Components */}
      {loading && !health && (
        <div className="flex items-center justify-center h-40">
          <div className="animate-spin w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full" />
        </div>
      )}

      {health && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Object.entries(health.components).map(([name, comp]) => (
            <ComponentCard key={name} name={name} health={comp as ComponentHealth} />
          ))}
        </div>
      )}

      {!health && !loading && (
        <div className="card-base p-8 text-center">
          <div className="text-4xl mb-3">🔌</div>
          <h3 className="text-slate-200 font-medium mb-2">Cannot Reach Backend</h3>
          <p className="text-slate-400 text-sm">The API server may be starting up or unreachable.</p>
        </div>
      )}
    </div>
  )
}

export default SystemHealthPage
