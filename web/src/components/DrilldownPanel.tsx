import { useState } from 'react'
import WeeklyTrendChart from './charts/WeeklyTrendChart'
import { AtRiskStudent, DrillLevel, WeeklyStat } from '../types'

const DANGER_HEX  = '#e74c3c'
const WARNING_HEX = '#f5a623'

type SortCol = 'present' | 'absent' | 'attendance_rate'
type SortDir = 'asc' | 'desc'

function rateColor(rate: number) {
  if (rate < 70) return 'text-danger'
  if (rate < 80) return 'text-warning'
  return 'text-success'
}

function rowStyle(rate: number): string {
  const base = 'border-b border-arctic-mist transition-colors'
  if (rate < 70) return `${base} border-l-4 border-l-danger bg-red-50 hover:bg-red-100/60`
  return `${base} border-l-4 border-l-warning hover:bg-arctic-mist/50`
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

function SortTh({ col, label, active, dir, onSort }: {
  col:    SortCol
  label:  string
  active: boolean
  dir:    SortDir
  onSort: (col: SortCol) => void
}) {
  return (
    <th
      className="px-5 py-3 text-right text-xs text-pewter uppercase tracking-widest cursor-pointer select-none hover:text-carbon transition-colors"
      onClick={() => onSort(col)}
    >
      {label}
      <span className="ml-1 opacity-50">{active ? (dir === 'asc' ? '↑' : '↓') : '↕'}</span>
    </th>
  )
}

interface Props {
  drillLevel:   DrillLevel
  drillClass:   string | null
  drillStudent: number | null
  atRisk:       AtRiskStudent[]
  sparklines:   Record<string, (number | null)[]>
  loading:      boolean
  onInspect:    (studentId: number) => void
}

export default function DrilldownPanel({
  drillLevel, drillClass, drillStudent, atRisk, sparklines, loading, onInspect,
}: Props) {
  const [sortCol, setSortCol] = useState<SortCol>('attendance_rate')
  const [sortDir, setSortDir] = useState<SortDir>('asc')

  const toggleSort = (col: SortCol) => {
    if (col === sortCol) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortCol(col); setSortDir('asc') }
  }

  if (drillLevel === 'overview') return null

  if (drillLevel === 'class') {
    const students = drillClass
      ? atRisk.filter((s) => s.cls === drillClass)
      : atRisk

    const sorted = [...students].sort((a, b) => {
      const mult = sortDir === 'asc' ? 1 : -1
      return (a[sortCol] - b[sortCol]) * mult
    })

    return (
      <div className="bg-fog border border-arctic-mist rounded-[10px] overflow-hidden mb-8">
        <div className="px-5 py-4 border-b border-arctic-mist">
          <h3 className="text-sm font-semibold text-carbon">
            At-Risk Students{drillClass ? ` — ${drillClass}` : ''}
          </h3>
          <p className="text-xs text-pewter mt-0.5">Below 75% attendance threshold</p>
        </div>

        {sorted.length === 0 ? (
          <p className="text-xs text-pewter px-5 py-4">No at-risk students in this class.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <caption className="sr-only">At-risk students{drillClass ? ` for ${drillClass}` : ''}</caption>
              <thead>
                <tr className="border-b border-arctic-mist">
                  <th className="px-5 py-3 text-left text-xs text-pewter uppercase tracking-widest">Student</th>
                  <SortTh col="present"         label="Present" active={sortCol === 'present'}         dir={sortDir} onSort={toggleSort} />
                  <SortTh col="absent"          label="Absent"  active={sortCol === 'absent'}          dir={sortDir} onSort={toggleSort} />
                  <SortTh col="attendance_rate" label="Rate"    active={sortCol === 'attendance_rate'} dir={sortDir} onSort={toggleSort} />
                  <th className="px-5 py-3 text-left text-xs text-pewter uppercase tracking-widest">6-week trend</th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody>
                {sorted.map((s) => {
                  const spark = sparklines[String(s.student_id)]
                  return (
                    <tr key={s.student_id} className={rowStyle(s.attendance_rate)}>
                      <td className="px-5 py-3 text-carbon">{s.name ?? `#${s.student_id}`}</td>
                      <td className="px-5 py-3 text-right text-pewter font-mono text-xs">{s.present}</td>
                      <td className="px-5 py-3 text-right text-pewter font-mono text-xs">{s.absent}</td>
                      <td className={`px-5 py-3 text-right font-mono text-xs font-medium ${rateColor(s.attendance_rate)}`}>
                        {s.attendance_rate}%
                      </td>
                      <td className="px-5 py-3">
                        {spark && <Sparkline points={spark} rate={s.attendance_rate} />}
                      </td>
                      <td className="px-5 py-3">
                        <button
                          onClick={() => onInspect(s.student_id)}
                          className="text-xs text-link-blue hover:underline rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-link-blue"
                        >
                          Inspect
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    )
  }

  // drillLevel === 'student'
  if (drillStudent === null) return null
  const student   = atRisk.find((s) => s.student_id === drillStudent)
  const sparkRaw  = sparklines[String(drillStudent)] ?? []
  const weeklyData: WeeklyStat[] = sparkRaw.map((rate, i) => ({
    week:            `Week ${i + 1}`,
    total:           0,
    present:         0,
    absent:          0,
    late:            0,
    attendance_rate: rate ?? 0,
  }))

  return (
    <div className="bg-fog border border-arctic-mist rounded-[10px] overflow-hidden mb-8">
      <div className="px-5 py-4 border-b border-arctic-mist">
        <h3 className="text-sm font-semibold text-carbon">
          {student?.name ?? `Student #${drillStudent}`}
        </h3>
        {student && (
          <p className="text-xs text-pewter mt-0.5">
            {student.cls} · {student.attendance_rate}% attendance
          </p>
        )}
      </div>
      <div className="p-5">
        <WeeklyTrendChart data={weeklyData} loading={loading} />
      </div>
    </div>
  )
}
