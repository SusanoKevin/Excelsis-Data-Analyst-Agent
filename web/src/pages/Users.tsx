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

  const fieldClass = "w-full bg-snow border border-arctic-mist rounded-input px-4 py-2.5 text-sm text-carbon placeholder-stone focus:outline-none focus:ring-2 focus:ring-link-blue"

  return (
    <div className="flex h-screen bg-snow">
      <Sidebar />

      <div className="flex-1 overflow-y-auto px-6 py-8 min-w-0">
        <h2 className="text-lg font-semibold text-carbon mb-8">User Management</h2>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Create form */}
          <div className="bg-fog border border-arctic-mist rounded-[10px] p-6">
            <h3 className="text-sm font-semibold text-carbon mb-1">Add User</h3>
            <p className="text-xs text-pewter mb-5">Create a new account</p>
            {msg   && <p className="text-success text-xs mb-3">{msg}</p>}
            {error && <p className="text-danger  text-xs mb-3">{error}</p>}
            <form onSubmit={create} className="space-y-3">
              <input className={fieldClass} placeholder="Username"
                value={username} onChange={(e) => setUsername(e.target.value)} required />
              <input className={fieldClass} placeholder="Password" type="password"
                value={password} onChange={(e) => setPassword(e.target.value)} required />
              <select className={fieldClass} value={role} onChange={(e) => setRole(e.target.value)}>
                {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
              <input className={fieldClass}
                placeholder="Allowed classes e.g. 10A, 10B — leave empty for all"
                value={classes} onChange={(e) => setClasses(e.target.value)} />
              <button
                type="submit"
                className="w-full bg-carbon text-white font-medium py-2.5 rounded-pill text-sm hover:opacity-90 transition-opacity mt-1"
              >
                Create user
              </button>
            </form>
          </div>

          {/* User list */}
          <div className="bg-fog border border-arctic-mist rounded-[10px] overflow-hidden">
            <div className="px-5 py-4 border-b border-arctic-mist">
              <h3 className="text-sm font-semibold text-carbon">Existing Users</h3>
              <p className="text-xs text-pewter mt-0.5">{users.length} account{users.length !== 1 ? 's' : ''}</p>
            </div>
            <ul>
              {users.map((u) => (
                <li key={u.username}
                  className="flex items-center justify-between px-5 py-3.5 border-b border-arctic-mist hover:bg-arctic-mist/50 transition-colors">
                  <div>
                    <p className="text-sm text-carbon font-medium">{u.username}</p>
                    <p className="text-xs text-stone capitalize mt-0.5">
                      {u.role}
                      {u.allowed_classes.length > 0 && ` · ${u.allowed_classes.join(', ')}`}
                    </p>
                  </div>
                  {u.username !== 'admin' && (
                    <button onClick={() => remove(u.username)}
                      className="text-xs text-stone hover:text-danger transition-colors">
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
