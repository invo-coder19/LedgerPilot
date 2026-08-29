import React, { useState, useRef, useEffect } from 'react'
import { investigationService } from '../services/investigationService'

interface Message {
  role: 'user' | 'assistant'
  content: string
  evidence?: Array<{ id: string; title: string; source_type: string }>
  timestamp: string
}

const EXAMPLE_QUESTIONS = [
  'What are the largest unresolved exceptions?',
  'How much value is currently unreconciled?',
  'Show me all fee variances',
  'Why is this exception unresolved?',
]

export default function FinanceCopilot() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (question: string) => {
    if (!question.trim() || loading) return
    const userMsg: Message = {
      role: 'user',
      content: question,
      timestamp: new Date().toLocaleTimeString(),
    }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await investigationService.askCopilot({ question })
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: res.answer,
          evidence: res.evidence_used,
          timestamp: new Date().toLocaleTimeString(),
        },
      ])
    } catch {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: 'Finance Copilot is temporarily unavailable. Please try again later.',
          timestamp: new Date().toLocaleTimeString(),
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      {/* Floating button */}
      <button
        id="copilot-toggle-btn"
        onClick={() => setOpen(v => !v)}
        className={`fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full shadow-2xl flex items-center justify-center text-xl transition-all duration-300 ${
          open
            ? 'bg-slate-700 hover:bg-slate-600 rotate-0'
            : 'bg-gradient-to-br from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 shadow-violet-500/30'
        }`}
        title="Finance Copilot"
      >
        {open ? '✕' : '💬'}
      </button>

      {/* Chat window */}
      {open && (
        <div className="fixed bottom-24 right-6 z-50 w-96 max-h-[600px] flex flex-col rounded-2xl border border-slate-700/60 bg-slate-900/95 backdrop-blur-xl shadow-2xl shadow-black/50 overflow-hidden animate-slide-up">
          {/* Header */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-700/50 bg-gradient-to-r from-violet-900/30 to-indigo-900/30">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-500 to-indigo-500 flex items-center justify-center text-sm">
              🧑‍💼
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-slate-100">Finance Copilot</p>
              <p className="text-xs text-slate-500">Powered by LedgerPilot AI · Read-only</p>
            </div>
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0" style={{ maxHeight: '380px' }}>
            {messages.length === 0 && (
              <div className="space-y-3">
                <p className="text-xs text-slate-500 text-center">Ask questions about your financial data</p>
                <div className="grid grid-cols-1 gap-2">
                  {EXAMPLE_QUESTIONS.map((q, i) => (
                    <button
                      key={i}
                      onClick={() => sendMessage(q)}
                      className="text-left text-xs px-3 py-2 rounded-lg border border-slate-700/50 bg-slate-800/40 text-slate-400 hover:bg-slate-700/40 hover:text-slate-300 transition-colors"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className={`flex gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <div className={`w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center text-xs ${
                  msg.role === 'user' ? 'bg-violet-600' : 'bg-slate-700'
                }`}>
                  {msg.role === 'user' ? '👤' : '🤖'}
                </div>
                <div className={`max-w-[80%] space-y-1 ${msg.role === 'user' ? 'items-end' : 'items-start'} flex flex-col`}>
                  <div className={`px-3 py-2 rounded-2xl text-xs leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-violet-600 text-white rounded-tr-sm'
                      : 'bg-slate-800 text-slate-300 rounded-tl-sm border border-slate-700/50'
                  }`}>
                    {msg.content}
                  </div>
                  {msg.evidence && msg.evidence.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {msg.evidence.map((e, j) => (
                        <span key={j} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-700/60 text-slate-500 font-mono">
                          {e.source_type}
                        </span>
                      ))}
                    </div>
                  )}
                  <span className="text-[10px] text-slate-600">{msg.timestamp}</span>
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex gap-2">
                <div className="w-7 h-7 rounded-full bg-slate-700 flex items-center justify-center text-xs">🤖</div>
                <div className="px-3 py-2 rounded-2xl rounded-tl-sm bg-slate-800 border border-slate-700/50">
                  <div className="flex gap-1">
                    {[0, 1, 2].map(i => (
                      <div key={i} className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-bounce" style={{ animationDelay: `${i * 150}ms` }} />
                    ))}
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="p-3 border-t border-slate-700/50 bg-slate-800/30">
            <form
              onSubmit={e => { e.preventDefault(); sendMessage(input) }}
              className="flex gap-2"
            >
              <input
                id="copilot-input"
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder="Ask about your financial data…"
                disabled={loading}
                className="flex-1 px-3 py-2 rounded-xl bg-slate-800 border border-slate-700/50 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-violet-500/50 disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="w-9 h-9 rounded-xl bg-violet-600 hover:bg-violet-500 disabled:opacity-40 flex items-center justify-center transition-colors"
              >
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </form>
            <p className="text-[10px] text-slate-600 mt-1.5 text-center">Read-only · Answers based on your LedgerPilot data</p>
          </div>
        </div>
      )}
    </>
  )
}
