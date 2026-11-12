import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.js'

export default function RoleGate({ role, children }) {
  const { user } = useAuth()

  if (!user) return null
  if (user.role !== role) return <Navigate to="/" replace />

  return children
}
