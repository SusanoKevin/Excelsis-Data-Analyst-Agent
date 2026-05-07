import { useEffect, useState } from 'react'
import Sidebar from '../components/Sidebar'
import api from '../api/client'
import { AttendanceSummary, AtRiskStudent } from '../types'

function KpiCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="bg-surface border border-border rounded-xl p-5">
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      <p className="text-2xl font-bold" style={{ color }}>{value}</p>
    </div>
  )
}

function rateColor(rate: number) {
  if (rate < 70) return 'text-danger'
  if (rate < 80) return 'text-warning'
  return 'text-success'
}

export default function Dashboard() {
  const [summary, setSummary]   = useState<AttendanceSummary | null>(null)
  const [atRisk, setAtRisk]     = useState<AtRiskStudent[]>([])
  const [imgUrl, setImgUrl]     = useState('')
  const [generating, setGen]    = useState(false)
  const [error, setError]       = useState('')

  useEffect(() => {
    api.get('/data/summary').then((r) => setSummary(r.data)).catch(() => {})
    api.get('/data/at-risk').then((r) => setAtRisk(r.data)).catch(() => {})
    api.get('/dashboard/latest').then((r) => { if (r.data.url) setImgUrl(r.data.url) }).catch(() => {})
  }, [])

  const generate = async () => {
    setGen(true)
    setError('')
    try {
      const { data } = await api.post('/dashboard/generate')
      setImgUrl(data.url + '?t=' + Date.now())
    } catch {
      setError('Failed to generate dashboard')
    } finally {
      setGen(false)
    }
  }

  return (
    <div className="flex h-screen">
      <Sidebar />

      <div className="flex-1 overflow-y-auto px-6 py-6 min-w-0">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold text-white">Attendance Dashboard</h2>
            {summary?.date_range && (
              <p className="text-xs text-slate-400">
                {summary.date_range.from} → {summary.date_range.to}
              </p>
            )}
          </div>
          <button
            onClick={generate}
            disabled={generating}
            className="bg-accent hover:bg-accent/80 disabled:opacity-50 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
          >
            {generating ? 'Generating…' : 'Generate Dashboard'}
          </button>
        </div>

        {/* KPI cards */}
        {summary && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <KpiCard label="Attendance rate"  value={`${summary.overall_attendance_rate}%`} color="#00a86b" />
            <KpiCard label="Total records"    value={summary.total_records.toLocaleString()}    color="#3498db" />
            <KpiCard label="Students"         value={summary.unique_students.toLocaleString()}  color="#38bdf8" />
            <KpiCard label="Total absences"   value={summary.total_absences.toLocaleString()}   color="#e74c3c" />
          </div>
        )}

        {error && <p className="text-danger text-sm mb-4">{error}</p>}

        {/* Dashboard image */}
        {imgUrl && (
          <div className="bg-surface border border-border rounded-xl p-4 mb-6">
            <img src={imgUrl} alt="Attendance dashboard" className="w-full rounded-lg" />
          </div>
        )}

        {/* At-risk table */}
        {atRisk.length > 0 && (
          <div className="bg-surface border border-border rounded-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-border">
              <h3 className="text-sm font-semibold text-white">At-Risk Students</h3>
              <p className="text-xs text-slate-400">Below 75% attendance threshold</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-xs text-slate-400">
                    <th className="px-5 py-3 text-left">Student</th>
                    <th className="px-5 py-3 text-left">Class</th>
                    <th className="px-5 py-3 text-right">Present</th>
                    <th className="px-5 py-3 text-right">Absent</th>
                    <th className="px-5 py-3 text-right">Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {atRisk.map((s, i) => (
                    <tr key={i} className="border-b border-border/50 hover:bg-[#0f172a]/40">
                      <td className="px-5 py-3 text-white">{s.name ?? `#${s.student_id}`}</td>
                      <td className="px-5 py-3 text-slate-300">{s.cls ?? '—'}</td>
                      <td className="px-5 py-3 text-right text-slate-300">{s.present}</td>
                      <td className="px-5 py-3 text-right text-slate-300">{s.absent}</td>
                      <td className={`px-5 py-3 text-right font-semibold ${rateColor(s.attendance_rate)}`}>
                        {s.attendance_rate}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {!summary && <p className="text-slate-400 text-sm">No data loaded yet. Upload a file or generate sample data.</p>}
      </div>
    </div>
  )
}
