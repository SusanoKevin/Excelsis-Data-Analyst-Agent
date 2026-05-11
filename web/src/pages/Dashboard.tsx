import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import Sidebar from '../components/Sidebar'
import ChatPanel from '../components/ChatPanel'
import api from '../api/client'
import { AttendanceSummary, AtRiskStudent } from '../types'

type SparklineMap = Record<string, (number | null)[]>

const DANGER_HEX  = '#e74c3c'
const WARNING_HEX = '#f5a623'

function KpiCard({ label, value, sub, featured }: {
  label: string; value: string; sub?: string; featured?: boolean
}) {
  return (
    <div className={`bg-fog rounded-[10px] p-5 ${
      featured
        ? 'border border-arctic-mist border-l-4 border-l-carbon'
        : 'border border-arctic-mist'
    }`}>
      <p className="text-xs text-stone uppercase tracking-widest mb-3">{label}</p>
      <p className={`text-carbon font-semibold ${featured ? 'text-4xl' : 'text-2xl'}`}>{value}</p>
      {sub && <p className="text-xs text-pewter mt-1">{sub}</p>}
    </div>
  )
}

function rowStyle(rate: number): string {
  const base = 'border-b border-arctic-mist transition-colors'
  if (rate < 70) return `${base} border-l-4 border-l-danger bg-red-50 hover:bg-red-100/60`
  return `${base} border-l-4 border-l-warning hover:bg-arctic-mist/50`
}

function rateColor(rate: number) {
  if (rate < 70) return 'text-danger'
  if (rate < 80) return 'text-warning'
  return 'text-success'
}

function Sparkline({ points, rate }: { points: (number | null)[], rate: number }) {
  const W = 56, H = 20
  const valid = points.filter((p): p is number => p !== null)
  if (valid.length < 2) return <span className="w-14 inline-block" />

  const segs: string[] = []
  let open = false
  points.forEach((p, i) => {
    if (p === null) { open = false; return }
    const x = (i / (points.length - 1)) * W
    const y = H - (p / 100) * H
    segs.push(`${open ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`)
    open = true
  })

  return (
    <svg width={W} height={H} className="overflow-visible" aria-hidden="true">
      <path
        d={segs.join(' ')}
        fill="none"
        stroke={rate < 70 ? DANGER_HEX : WARNING_HEX}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export default function Dashboard() {
  const [summary, setSummary]   = useState<AttendanceSummary | null>(null)
  const [atRisk, setAtRisk]     = useState<AtRiskStudent[]>([])
  const [sparklines, setSpark]  = useState<SparklineMap>({})
  const [imgUrl, setImgUrl]     = useState('')
  const [generating, setGen]    = useState(false)
  const [panelOpen, setPanel]   = useState(false)

  useEffect(() => {
    api.get('/data/summary').then((r) => setSummary(r.data)).catch(() => {})
    api.get('/data/at-risk').then((r) => {
      setAtRisk(r.data)
      if (r.data.length > 0) {
        const ids = r.data.map((s: AtRiskStudent) => s.student_id).join(',')
        api.get(`/data/sparklines?ids=${ids}`).then((sr) => setSpark(sr.data)).catch(() => {})
      }
    }).catch(() => {})
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

        <div className="flex items-start justify-between mb-8">
          <div>
            <h2 className="font-serif text-2xl font-normal text-carbon">Attendance Dashboard</h2>
            {summary?.date_range && (
              <p className="text-xs text-pewter mt-1">
                {summary.date_range.from} — {summary.date_range.to}
              </p>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setPanel((p) => !p)}
              className={`text-sm rounded-[10px] px-4 py-2 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-link-blue focus-visible:ring-offset-2 ${
                panelOpen
                  ? 'bg-arctic-mist text-carbon'
                  : 'bg-fog border border-arctic-mist text-pewter hover:text-carbon hover:border-stone'
              }`}
            >
              {panelOpen ? 'Close chat' : 'Ask Excelsis'}
            </button>
            <button
              onClick={generate}
              disabled={generating}
              className="bg-carbon text-white disabled:opacity-30 text-sm rounded-[10px] px-4 py-2 hover:opacity-90 transition-opacity focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-link-blue focus-visible:ring-offset-2"
            >
              {generating ? 'Generating…' : 'Generate Dashboard'}
            </button>
          </div>
        </div>

        {summary && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <KpiCard label="Attendance rate" value={`${summary.overall_attendance_rate}%`} featured />
            <KpiCard label="Total records"   value={summary.total_records.toLocaleString()} />
            <KpiCard label="Students"        value={summary.unique_students.toLocaleString()} />
            <KpiCard label="Total absences"  value={summary.total_absences.toLocaleString()} />
          </div>
        )}

        {imgUrl && (
          <div className="mb-8">
            <iframe
              src={imgUrl}
              title="Attendance dashboard"
              className="w-full border-0 block"
              style={{ height: '740px' }}
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

        {atRisk.length > 0 && (
          <div className="bg-fog border border-arctic-mist rounded-[10px] overflow-hidden">
            <div className="px-5 py-4 border-b border-arctic-mist">
              <h3 className="text-sm font-semibold text-carbon">At-Risk Students</h3>
              <p className="text-xs text-pewter mt-0.5">Below 75% attendance threshold</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <caption className="sr-only">At-risk students below 75% attendance threshold</caption>
                <thead>
                  <tr className="border-b border-arctic-mist">
                    <th className="px-5 py-3 text-left text-xs text-stone uppercase tracking-widest">Student</th>
                    <th className="px-5 py-3 text-left text-xs text-stone uppercase tracking-widest">Class</th>
                    <th className="px-5 py-3 text-right text-xs text-stone uppercase tracking-widest">Present</th>
                    <th className="px-5 py-3 text-right text-xs text-stone uppercase tracking-widest">Absent</th>
                    <th className="px-5 py-3 text-right text-xs text-stone uppercase tracking-widest">Rate</th>
                    <th className="px-5 py-3 text-left text-xs text-stone uppercase tracking-widest">6-week trend</th>
                  </tr>
                </thead>
                <tbody>
                  {atRisk.map((s, i) => {
                    const spark = sparklines[String(s.student_id)]
                    return (
                      <tr key={i} className={rowStyle(s.attendance_rate)}>
                        <td className="px-5 py-3 text-carbon">{s.name ?? `#${s.student_id}`}</td>
                        <td className="px-5 py-3 text-pewter">{s.cls ?? '—'}</td>
                        <td className="px-5 py-3 text-right text-pewter font-mono text-xs">{s.present}</td>
                        <td className="px-5 py-3 text-right text-pewter font-mono text-xs">{s.absent}</td>
                        <td
                          className={`px-5 py-3 text-right font-mono text-xs font-medium ${rateColor(s.attendance_rate)}`}
                          aria-label={`${s.attendance_rate}%, ${s.attendance_rate < 70 ? 'critical' : 'at risk'}`}
                        >
                          {s.attendance_rate}%
                        </td>
                        <td className="px-5 py-3">
                          {spark && <Sparkline points={spark} rate={s.attendance_rate} />}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {!summary && (
          <p className="text-sm text-pewter">No data loaded yet. Upload a file or generate sample data.</p>
        )}

      </div>

      {panelOpen && (
        <ChatPanel atRisk={atRisk} summary={summary} onClose={() => setPanel(false)} />
      )}
    </div>
  )
}
