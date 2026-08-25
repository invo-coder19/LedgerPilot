import React, { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { getErrorMessage } from '../utils/format'

const LoginPage: React.FC = () => {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/dashboard'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)
    try {
      await login(email, password)
      navigate(from, { replace: true })
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setIsLoading(false)
    }
  }

  const fillDemo = (role: string) => {
    const credentials: Record<string, [string, string]> = {
      admin:   ['admin@ledgerpilot.dev', 'Admin@123'],
      manager: ['manager@ledgerpilot.dev', 'Manager@123'],
      analyst: ['analyst@ledgerpilot.dev', 'Analyst@123'],
      viewer:  ['viewer@ledgerpilot.dev', 'Viewer@123'],
    }
    const [e, p] = credentials[role]
    setEmail(e)
    setPassword(p)
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 bg-brand-500 rounded-xl flex items-center justify-center mb-4 shadow-lg">
            <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-slate-100">LedgerPilot</h1>
          <p className="text-sm text-slate-400 mt-1">AI Finance Controller</p>
        </div>

        {/* Form card */}
        <div className="card p-8">
          <h2 className="text-lg font-semibold text-slate-100 mb-6">Sign in to your account</h2>

          {error && (
            <div className="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}

          <form id="login-form" onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email-input" className="label">Email address</label>
              <input
                id="email-input"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input"
                placeholder="admin@ledgerpilot.dev"
              />
            </div>
            <div>
              <label htmlFor="password-input" className="label">Password</label>
              <input
                id="password-input"
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input"
                placeholder="••••••••"
              />
            </div>
            <button
              id="login-submit-btn"
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full justify-center py-2.5"
            >
              {isLoading ? (
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : null}
              {isLoading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          {/* Demo credentials */}
          <div className="mt-6 pt-5 border-t border-surface-border">
            <p className="text-xs text-slate-500 mb-3 uppercase tracking-wide font-medium">Demo credentials</p>
            <div className="grid grid-cols-2 gap-2">
              {['admin', 'manager', 'analyst', 'viewer'].map((role) => (
                <button
                  key={role}
                  id={`demo-${role}-btn`}
                  type="button"
                  onClick={() => fillDemo(role)}
                  className="px-3 py-2 rounded-lg text-xs font-medium text-slate-400 border border-surface-border hover:bg-surface-hover hover:text-slate-200 transition-colors"
                >
                  {role.charAt(0).toUpperCase() + role.slice(1)}
                </button>
              ))}
            </div>
            <p className="text-xs text-slate-600 mt-3 text-center">
              Click a role to fill in credentials
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default LoginPage
