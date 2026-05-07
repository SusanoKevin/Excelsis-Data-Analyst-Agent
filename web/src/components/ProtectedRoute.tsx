import { Navigate } from 'react-router-dom'
import { useAuth } from '../App'

interface Props {
  children: React.ReactNode
  adminOnly?: boolean
}

export default function ProtectedRoute({ children, adminOnly = false }: Props) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (adminOnly && user.role !== 'admin') return <Navigate to="/chat" replace />
  return <>{children}</>
}
