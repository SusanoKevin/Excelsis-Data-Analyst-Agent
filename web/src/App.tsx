import { createContext, useContext, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Toaster } from 'sonner'
import Login from './pages/Login'
import Chat from './pages/Chat'
import Dashboard from './pages/Dashboard'
import Users from './pages/Users'
import ProtectedRoute from './components/ProtectedRoute'
import { AuthUser } from './types'

interface AuthCtx {
  user: AuthUser | null
  login: (u: AuthUser) => void
  logout: () => void
}

export const AuthContext = createContext<AuthCtx>({
  user: null, login: () => {}, logout: () => {},
})
export const useAuth = () => useContext(AuthContext)

function loadUser(): AuthUser | null {
  const token = localStorage.getItem('token')
  const role  = localStorage.getItem('role')
  const userId = localStorage.getItem('userId')
  if (!token || !role || !userId) return null
  const allowedClasses = JSON.parse(localStorage.getItem('allowedClasses') ?? '[]')
  return { token, role, userId, allowedClasses }
}

export default function App() {
  const [user, setUser] = useState<AuthUser | null>(loadUser)

  const login = (u: AuthUser) => {
    localStorage.setItem('token',          u.token)
    localStorage.setItem('role',           u.role)
    localStorage.setItem('userId',         u.userId)
    localStorage.setItem('allowedClasses', JSON.stringify(u.allowedClasses))
    setUser(u)
  }

  const logout = () => {
    localStorage.clear()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      <Toaster position="bottom-right" theme="dark" richColors />
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Navigate to="/chat" replace />} />
          <Route path="/chat" element={<ProtectedRoute><Chat /></ProtectedRoute>} />
          <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/users" element={<ProtectedRoute adminOnly><Users /></ProtectedRoute>} />
        </Routes>
      </BrowserRouter>
    </AuthContext.Provider>
  )
}
