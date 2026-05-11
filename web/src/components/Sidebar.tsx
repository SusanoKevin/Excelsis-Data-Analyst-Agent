import { useRef } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { useAuth } from '../App'
import api from '../api/client'

const link = ({ isActive }: { isActive: boolean }) =>
  `flex items-center px-3 py-1.5 text-sm rounded-[10px] transition-colors ${
    isActive
      ? 'bg-arctic-mist text-carbon font-medium'
      : 'text-pewter hover:text-carbon hover:bg-arctic-mist'
  }`

export default function Sidebar() {
  const { user, logout } = useAuth()
  const navigate  = useNavigate()
  const fileInput = useRef<HTMLInputElement>(null)

  const canUpload = user?.role === 'admin' || user?.role === 'teacher'

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ''

    const id = toast.loading(`Uploading ${file.name}…`)
    const form = new FormData()
    form.append('file', file)
    try {
      const { data } = await api.post('/data/upload', form)
      toast.success(`Loaded ${data.rows.toLocaleString()} rows`, { id })
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? 'Upload failed'
      toast.error(detail, { id })
    }
  }

  return (
    <aside className="w-52 min-h-screen bg-fog border-r border-arctic-mist flex flex-col">
      {/* Logo */}
      <div className="px-5 py-6 border-b border-arctic-mist">
        <p className="text-xs text-stone uppercase tracking-widest mb-1">Excelsis 360</p>
        <p className="text-sm text-carbon font-semibold">Attendance Analyst</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 px-3 space-y-0.5">
        <NavLink to="/chat"      className={link}>Chat</NavLink>
        <NavLink to="/dashboard" className={link}>Dashboard</NavLink>
        {user?.role === 'admin' && (
          <NavLink to="/users"   className={link}>Users</NavLink>
        )}
      </nav>

      {/* User info + actions */}
      <div className="p-5 border-t border-arctic-mist">
        <p className="text-xs text-carbon font-medium truncate">{user?.userId}</p>
        <p className="text-xs text-stone capitalize mb-4">{user?.role}</p>

        <input
          ref={fileInput}
          type="file"
          accept=".csv,.xlsx,.xls,.parquet"
          className="hidden"
          onChange={handleFile}
        />

        <div className="flex flex-col gap-2">
          {canUpload && (
            <button
              onClick={() => fileInput.current?.click()}
              className="text-sm text-pewter hover:text-carbon transition-colors text-left"
            >
              Upload data ↑
            </button>
          )}
          <button
            onClick={() => { logout(); navigate('/login') }}
            className="text-sm text-pewter hover:text-carbon transition-colors text-left"
          >
            Sign out →
          </button>
        </div>
      </div>
    </aside>
  )
}
