import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import { useAuth } from '../App'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data } = await api.post('/auth/login', { username, password })
      login({
        token:          data.access_token,
        role:           data.role,
        userId:         data.user_id,
        allowedClasses: data.allowed_classes,
      })
      navigate('/chat')
    } catch (err: any) {
      setError(err.response?.data?.detail ?? 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0f172a]">
      <div className="w-full max-w-sm">
        {/* Header */}
        <div className="text-center mb-8">
          <p className="text-xs text-slate-500 uppercase tracking-widest mb-1">Excelsis 360</p>
          <h1 className="text-2xl font-bold text-white">Attendance Analyst</h1>
        </div>

        <form
          onSubmit={submit}
          className="bg-surface border border-border rounded-2xl p-8 space-y-5"
        >
          {error && (
            <p className="text-danger text-sm text-center bg-danger/10 border border-danger/30 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <div>
            <label className="block text-xs text-slate-400 mb-1.5">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
              className="w-full bg-[#0f172a] border border-border rounded-lg px-4 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-accent"
              placeholder="admin"
            />
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1.5">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full bg-[#0f172a] border border-border rounded-lg px-4 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-accent"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-accent hover:bg-accent/90 disabled:opacity-50 text-white font-medium py-2.5 rounded-lg transition-colors text-sm"
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
