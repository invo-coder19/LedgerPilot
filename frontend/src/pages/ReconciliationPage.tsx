import React from 'react'

const DataSourceCard: React.FC<{ title: string; description: string; count?: number; link: string }> = ({
  title, description, link,
}) => (
  <a
    href={link}
    className="card p-5 hover:shadow-card-hover transition-shadow block"
  >
    <div className="flex items-center justify-between mb-3">
      <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
      <span className="text-brand-400 text-xs">View →</span>
    </div>
    <p className="text-xs text-slate-500">{description}</p>
  </a>
)

const ReconciliationPage: React.FC = () => (
  <div className="p-6 space-y-6 animate-fade-in">
    <div>
      <h1 className="text-xl font-bold text-slate-100">Reconciliation</h1>
      <p className="text-sm text-slate-400 mt-0.5">Financial data sources and reconciliation controls</p>
    </div>

    {/* Data sources */}
    <div>
      <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-3">Data Sources</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <DataSourceCard
          title="Transactions"
          description="Payment transaction records from the payment gateway."
          link="/transactions"
        />
        <DataSourceCard
          title="Invoices"
          description="Customer invoices issued and their payment status."
          link="/invoices"
        />
        <DataSourceCard
          title="Settlements"
          description="Settlement batches from the payment processor."
          link="/settlements"
        />
        <DataSourceCard
          title="Bank Transactions"
          description="Bank account statement entries and credits."
          link="/bank-transactions"
        />
      </div>
    </div>

    {/* Engine placeholder */}
    <div className="card p-8 border-dashed border-2 border-surface-border text-center">
      <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-surface mb-4">
        <svg className="w-8 h-8 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
        </svg>
      </div>
      <h2 className="text-lg font-bold text-slate-300 mb-2">Reconciliation Engine</h2>
      <p className="text-sm text-slate-500 max-w-md mx-auto mb-4">
        The automated reconciliation engine will match transactions against invoices, settlements,
        and bank records — identifying discrepancies and flagging exceptions automatically.
      </p>
      <span className="badge bg-blue-500/10 text-blue-400 border border-blue-500/20 px-3 py-1">
        Coming in Phase 2
      </span>

      <div className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4 text-left">
        {[
          {
            phase: 'Phase 2',
            title: 'Reconciliation Engine',
            desc: 'RapidFuzz matching, Pandas/NumPy processing, exception auto-detection',
          },
          {
            phase: 'Phase 3',
            title: 'Intelligence Layer',
            desc: 'LangGraph + LLM investigation, XGBoost anomaly detection, RAG explanations',
          },
          {
            phase: 'Phase 4',
            title: 'Autonomous Controller',
            desc: 'Celery workflows, confidence gating, human-in-the-loop approvals',
          },
        ].map((item) => (
          <div key={item.phase} className="p-4 bg-surface rounded-xl opacity-60">
            <span className="badge bg-slate-500/10 text-slate-400 border border-slate-500/20 mb-2">{item.phase}</span>
            <h3 className="text-sm font-semibold text-slate-300 mt-2">{item.title}</h3>
            <p className="text-xs text-slate-500 mt-1">{item.desc}</p>
          </div>
        ))}
      </div>
    </div>
  </div>
)

export default ReconciliationPage
