import { FormEvent, useEffect, useState } from 'react'
import Sidebar from '../components/Sidebar'
import api from '../api/client'
import { UserRecord } from '../types'

const ROLES = ['admin', 'teacher', 'counselor', 'viewer']

export default function Users() {
  const [users, setUsers]       = useState<UserRecord[]>([])
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole]         = useState('teacher')
  const [classes, setClasses]   = useState('')
  const [msg, setMsg]           = useState('')
  const [error, setError]       = useState('')

  const load = () => api.get('/auth/users').then((r) => setUsers(r.data)).catch(() => {})
  useEffect(() => { load() }, [])

  const create = async (e: FormEvent) => {
    e.preventDefault()
    setMsg(''); setError('')
    try {
      await api.post('/auth/users', {
        username,
        password,
        role,
        allowed_classes: classes.split(',').map((c) => c.trim()).filter(Boolean),
      })
      setMsg(`User '${username}' created`)
      setUsername(''); setPassword(''); setClasses('')
      load()
    } catch (err: any) {
      setError(err.response?.data?.detail ?? 'Failed to create user')
    }
  }

  const remove = async (u: string) => {
    if (!confirm(`Delete user '${u}'?`)) return
    await api.delete(`/auth/users/${u}`).catch(() => {})
    load()
  }

  const fieldClass = "w-full bg-[#0f172a] border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-accent"

  return (
    <div className="flex h-screen">
      <Sidebar />

      <div className="flex-1 overflow-y-auto px-6 py-6 min-w-0">
        <h2 className="text-lg font-semibold text-white mb-6">User Management</h2>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Create form */}
          <div className="bg-surface border border-border rounded-xl p-6">
            <h3 className="text-sm font-semibold text-white mb-4">Add User</h3>
            {msg   && <p className="text-success text-xs mb-3">{msg}</p>}
            {error && <p className="text-danger  text-xs mb-3">{error}</p>}
            <form onSubmit={create} className="space-y-3">
              <input className={fieldClass} placeholder="Username" value={username}
                onChange={(e) => setUsername(e.target.value)} required />
              <input className={fieldClass} placeholder="Password" type="password" value={password}
                onChange={(e) => setPassword(e.target.value)} required />
              <select className={fieldClass} value={role} onChange={(e) => setRole(e.target.value)}>
                {ROLES.map((r) => <option key={r}>{r}</option>)}
              </select>
              <input className={fieldClass} placeholder="Allowed classes (e.g. 10A, 10B) — leave empty for all"
                value={classes} onChange={(e) => setClasses(e.target.value)} />
              <button type="submit"
                className="w-full bg-accent hover:bg-accent/80 text-white text-sm font-medium py-2 rounded-lg transition-colors">
                Create user
              </button>
            </form>
          </div>

          {/* User list */}
          <div className="bg-surface border border-border rounded-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-border">
              <h3 className="text-sm font-semibold text-white">Existing Users</h3>
            </div>
            <ul>
              {users.map((u) => (
                <li key={u.username}
                  className="flex items-center justify-between px-5 py-3 border-b border-border/50 hover:bg-[#0f172a]/30">
                  <div>
                    <p className="text-sm text-white font-medium">{u.username}</p>
                    <p className="text-xs text-slate-400 capitalize">
                      {u.role}
                      {u.allowed_classes.length > 0 && ` · ${u.allowed_classes.join(', ')}`}
                    </p>
                  </div>
                  {u.username !== 'admin' && (
                    <button onClick={() => remove(u.username)}
                      className="text-xs text-danger hover:text-white hover:bg-danger px-2 py-1 rounded transition-colors">
                      Remove
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
