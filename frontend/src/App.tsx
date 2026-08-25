import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './auth/AuthProvider'
import ProtectedRoute from './auth/ProtectedRoute'
import AppLayout from './layouts/AppLayout'

import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import TransactionsPage from './pages/TransactionsPage'
import TransactionDetailPage from './pages/TransactionDetailPage'
import InvoicesPage from './pages/InvoicesPage'
import SettlementsPage from './pages/SettlementsPage'
import BankTransactionsPage from './pages/BankTransactionsPage'
import ExceptionsPage from './pages/ExceptionsPage'
import ExceptionDetailPage from './pages/ExceptionDetailPage'
import AuditLogPage from './pages/AuditLogPage'
import SettingsPage from './pages/SettingsPage'
import ReconciliationPage from './pages/ReconciliationPage'

const App: React.FC = () => (
  <BrowserRouter>
    <AuthProvider>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected */}
        <Route
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/reconcile" element={<ReconciliationPage />} />
          <Route path="/transactions" element={<TransactionsPage />} />
          <Route path="/transactions/:id" element={<TransactionDetailPage />} />
          <Route path="/invoices" element={<InvoicesPage />} />
          <Route path="/settlements" element={<SettlementsPage />} />
          <Route path="/bank-transactions" element={<BankTransactionsPage />} />
          <Route path="/exceptions" element={<ExceptionsPage />} />
          <Route path="/exceptions/:id" element={<ExceptionDetailPage />} />
          <Route path="/audit-log" element={<AuditLogPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AuthProvider>
  </BrowserRouter>
)

export default App
