import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import Sidebar from '../components/Sidebar'
import api from '../api/client'
import { AttendanceSummary, AtRiskStudent } from '../types'

function KpiCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-fog border border-arctic-mist rounded-[10px] p-5">
      <p className="text-xs text-stone uppercase tracking-widest mb-3">{label}</p>
      <p className="text-2xl text-carbon font-semibold">{value}</p>
      {sub && <p className="text-xs text-pewter mt-1">{sub}</p>}
    </div>
  )
}

function rateColor(rate: number) {
  if (rate < 70) return 'text-danger'
  if (rate < 80) return 'text-warning'
  return 'text-success'
}

export default function Dashboard() {
  const [summary, setSummary] = useState<AttendanceSummary | null>(null)
  const [atRisk, setAtRisk]   = useState<AtRiskStudent[]>([])
  const [imgUrl, setImgUrl]   = useState('')
  const [generating, setGen]  = useState(false)

  useEffect(() => {
    api.get('/data/summary').then((r) => setSummary(r.data)).catch(() => {})
    api.get('/data/at-risk').then((r) => setAtRisk(r.data)).catch(() => {})
    api.get('/dashboard/latest').then((r) => { if (r.data.url) setImgUrl(r.data.url) }).catch(() => {})
  }, [])

  const generate = async () => {
    setGen(true)
    const id = toast.loading('Generating dashboard…')
    try {
      const { data } = await api.post('/dashboard/generate')
      setImgUrl(data.url + '?t=' + Date.now())
      toast.success('Dashboard ready', { id })
    } catch {
      toast.error('Failed to generate dashboard', { id })
    } finally {
      setGen(false)
    }
  }

  return (
    <div className="flex h-screen bg-snow">
      <Sidebar />

      <div className="flex-1 overflow-y-auto px-6 py-8 min-w-0">

        {/* Page header */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <h2 className="text-lg font-semibold text-carbon">Attendance Dashboard</h2>
            {summary?.date_range && (
              <p className="text-xs text-pewter mt-1">
                {summary.date_range.from} — {summary.date_range.to}
              </p>
            )}
          </div>
          <button
            onClick={generate}
            disabled={generating}
            className="bg-carbon text-white disabled:opacity-30 text-sm rounded-[10px] px-4 py-2 hover:opacity-90 transition-opacity"
          >
            {generating ? 'Generating…' : 'Generate Dashboard'}
          </button>
        </div>

        {/* KPI cards */}
        {summary && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <KpiCard label="Attendance rate" value={`${summary.overall_attendance_rate}%`} />
            <KpiCard label="Total records"   value={summary.total_records.toLocaleString()} />
            <KpiCard label="Students"        value={summary.unique_students.toLocaleString()} />
            <KpiCard label="Total absences"  value={summary.total_absences.toLocaleString()} />
          </div>
        )}

        {/* Dashboard — merges seamlessly with page background */}
        {imgUrl && (
          <div className="mb-8">
            <iframe
              src={imgUrl}
              title="Attendance dashboard"
              className="w-full border-0 block"
              style={{ height: "740px" }}
              sandbox="allow-scripts allow-same-origin"
            />
            <div className="flex justify-end py-2">
              <a
                href={imgUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-stone hover:text-carbon transition-colors"
              >
                Open full screen ↗
              </a>
            </div>
          </div>
        )}

        {/* At-risk table */}
        {atRisk.length > 0 && (
          <div className="bg-fog border border-arctic-mist rounded-[10px] overflow-hidden">
            <div className="px-5 py-4 border-b border-arctic-mist">
              <h3 className="text-sm font-semibold text-carbon">At-Risk Students</h3>
              <p className="text-xs text-pewter mt-0.5">Below 75% attendance threshold</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-arctic-mist">
                    <th className="px-5 py-3 text-left text-xs text-stone uppercase tracking-widest">Student</th>
                    <th className="px-5 py-3 text-left text-xs text-stone uppercase tracking-widest">Class</th>
                    <th className="px-5 py-3 text-right text-xs text-stone uppercase tracking-widest">Present</th>
                    <th className="px-5 py-3 text-right text-xs text-stone uppercase tracking-widest">Absent</th>
                    <th className="px-5 py-3 text-right text-xs text-stone uppercase tracking-widest">Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {atRisk.map((s, i) => (
                    <tr key={i} className="border-b border-arctic-mist hover:bg-arctic-mist/50 transition-colors">
                      <td className="px-5 py-3 text-carbon">{s.name ?? `#${s.student_id}`}</td>
                      <td className="px-5 py-3 text-pewter">{s.cls ?? '—'}</td>
                      <td className="px-5 py-3 text-right text-pewter font-mono text-xs">{s.present}</td>
                      <td className="px-5 py-3 text-right text-pewter font-mono text-xs">{s.absent}</td>
                      <td className={`px-5 py-3 text-right font-mono text-xs font-medium ${rateColor(s.attendance_rate)}`}>
                        {s.attendance_rate}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {!summary && (
          <p className="text-sm text-pewter">No data loaded yet. Upload a file or generate sample data.</p>
        )}

      </div>
    </div>
  )
}
