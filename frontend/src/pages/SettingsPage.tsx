import React from 'react'
import { useAuth } from '../auth/useAuth'

const SettingsPage: React.FC = () => {
  const { user } = useAuth()

  return (
    <div className="p-6 max-w-2xl space-y-6 animate-fade-in">
      <div>
        <h1 className="text-xl font-bold text-slate-100">Settings</h1>
        <p className="text-sm text-slate-400 mt-0.5">Account and platform configuration</p>
      </div>

      {/* Profile */}
      <div className="card p-6 space-y-4">
        <h2 className="text-sm font-semibold text-slate-200 border-b border-surface-border pb-3">Profile</h2>
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-full bg-brand-500/20 flex items-center justify-center text-brand-400 font-bold text-xl">
            {user?.full_name?.[0] || 'U'}
          </div>
          <div>
            <p className="text-base font-semibold text-slate-100">{user?.full_name}</p>
            <p className="text-sm text-slate-400">{user?.email}</p>
            <span className="text-xs text-brand-400 font-medium">{user?.role?.replace(/_/g, ' ')}</span>
          </div>
        </div>
        <dl className="grid grid-cols-2 gap-4 pt-2">
          <div>
            <dt className="label">Account ID</dt>
            <dd className="text-xs font-mono text-slate-400">{user?.id}</dd>
          </div>
          <div>
            <dt className="label">Account Status</dt>
            <dd className="text-xs text-green-400">Active</dd>
          </div>
        </dl>
      </div>

      {/* Merchant */}
      <div className="card p-6 space-y-4">
        <h2 className="text-sm font-semibold text-slate-200 border-b border-surface-border pb-3">Merchant</h2>
        <dl className="grid grid-cols-2 gap-4">
          <div>
            <dt className="label">Business Name</dt>
            <dd className="text-sm text-slate-200">Acme Commerce Pvt Ltd</dd>
          </div>
          <div>
            <dt className="label">Currency</dt>
            <dd className="text-sm text-slate-200">INR (Indian Rupee)</dd>
          </div>
          <div>
            <dt className="label">Timezone</dt>
            <dd className="text-sm text-slate-200">Asia/Kolkata (IST)</dd>
          </div>
          <div>
            <dt className="label">Email</dt>
            <dd className="text-sm text-slate-200">accounts@acmecommerce.in</dd>
          </div>
        </dl>
      </div>

      {/* Platform */}
      <div className="card p-6 space-y-4">
        <h2 className="text-sm font-semibold text-slate-200 border-b border-surface-border pb-3">Platform</h2>
        <dl className="grid grid-cols-2 gap-4">
          <div>
            <dt className="label">Version</dt>
            <dd className="text-sm text-slate-200">1.0.0 — Phase 1</dd>
          </div>
          <div>
            <dt className="label">Phase</dt>
            <dd className="text-sm text-slate-200">Foundation & Dashboard</dd>
          </div>
        </dl>
        <div className="mt-2 p-4 bg-surface rounded-xl">
          <p className="text-xs text-slate-500">
            Advanced configuration including reconciliation engine settings, AI model parameters,
            and autonomous action thresholds will be available in Phase 2–4.
          </p>
        </div>
      </div>
    </div>
  )
}

export default SettingsPage
