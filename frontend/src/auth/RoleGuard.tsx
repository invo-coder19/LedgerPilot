import React from 'react'
import type { Role } from '../types'
import { useAuth } from './useAuth'

interface RoleGuardProps {
  roles: Role[]
  children: React.ReactNode
  fallback?: React.ReactNode
}

/**
 * Conditionally renders children only if the current user has one of the specified roles.
 * Shows optional fallback otherwise.
 */
const RoleGuard: React.FC<RoleGuardProps> = ({ roles, children, fallback = null }) => {
  const { user } = useAuth()

  if (!user || !roles.includes(user.role)) {
    return <>{fallback}</>
  }

  return <>{children}</>
}

export default RoleGuard
