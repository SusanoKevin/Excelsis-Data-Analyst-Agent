import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../App'

const link = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
    isActive
      ? 'bg-accent text-white'
      : 'text-slate-300 hover:bg-surface hover:text-white'
  }`

export default function Sidebar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <aside className="w-56 min-h-screen bg-[#0f172a] border-r border-border flex flex-col">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-border">
        <p className="text-xs text-slate-400 uppercase tracking-widest mb-1">Excelsis 360</p>
        <p className="text-base font-semibold text-white">Attendance Analyst</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-1">
        <NavLink to="/chat"      className={link}>💬 Chat</NavLink>
        <NavLink to="/dashboard" className={link}>📊 Dashboard</NavLink>
        {user?.role === 'admin' && (
          <NavLink to="/users" className={link}>👥 Users</NavLink>
        )}
      </nav>

      {/* User info + logout */}
      <div className="p-4 border-t border-border">
        <p className="text-xs text-slate-400 truncate">{user?.userId}</p>
        <p className="text-xs text-slate-500 capitalize mb-3">{user?.role}</p>
        <button
          onClick={handleLogout}
          className="w-full text-xs text-slate-400 hover:text-white hover:bg-surface px-3 py-2 rounded-lg transition-colors text-left"
        >
          Sign out →
        </button>
      </div>
    </aside>
  )
}
