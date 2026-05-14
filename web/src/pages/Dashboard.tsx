import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import ChatPanel from '../components/ChatPanel'
import FilterBar from '../components/FilterBar'
import Breadcrumb from '../components/Breadcrumb'
import DrilldownPanel from '../components/DrilldownPanel'
import AttendanceByClassChart from '../components/charts/AttendanceByClassChart'
import WeeklyTrendChart from '../components/charts/WeeklyTrendChart'
import StatusDonutChart from '../components/charts/StatusDonutChart'
import WeekdayBarChart from '../components/charts/WeekdayBarChart'
import { useDashboardData } from '../hooks/useDashboardData'
import { DashboardFilter, DashboardFilterEvent, DashboardPeriod, DrillLevel } from '../types'

function KpiCard({ label, value, sub, featured }: {
  label: string; value: string; sub?: string; featured?: boolean
}) {
  return (
    <div className={`bg-fog rounded-[10px] p-5 ${
      featured
        ? 'border border-arctic-mist border-l-4 border-l-carbon'
        : 'border border-arctic-mist'
    }`}>
      <p className="text-xs text-pewter uppercase tracking-widest mb-3">{label}</p>
      <p className={`text-carbon font-semibold ${featured ? 'text-4xl' : 'text-2xl'}`}>{value}</p>
      {sub && <p className="text-xs text-pewter mt-1">{sub}</p>}
    </div>
  )
}

export default function Dashboard() {
  const [searchParams] = useSearchParams()

  const [filter, setFilter]           = useState<DashboardFilter>({ classes: [], period: 'all', grade: '' })
  const [activeClass, setActiveClass]  = useState<string | null>(null)
  const [drillLevel, setDrillLevel]   = useState<DrillLevel>('overview')
  const [drillClass, setDrillClass]   = useState<string | null>(null)
  const [drillStudent, setDrillStudent] = useState<number | null>(null)
  const [panelOpen, setPanel]          = useState(false)

  // URL param initialization for "View in Dashboard" deep links
  useEffect(() => {
    const cls  = searchParams.get('classes')
    const per  = searchParams.get('period') as DashboardPeriod | null
    const view = searchParams.get('view')   as DrillLevel | null
    if (cls || per || view) {
      const classes = cls?.split(',').filter(Boolean) ?? []
      setFilter({ classes, period: per ?? 'all', grade: '' })
      if (view === 'class' && classes.length > 0) {
        setDrillLevel('class')
        setDrillClass(classes[0])
        setActiveClass(classes[0])
      }
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const { summary, classStats, weeklyStats, dowStats, statusCounts, atRisk, sparklines, loading } =
    useDashboardData(filter)

  const availableClasses = summary?.classes ?? []

  function handleClassClick(cls: string) {
    const next = activeClass === cls ? null : cls
    setActiveClass(next)
    setFilter((f) => ({ ...f, classes: next ? [next] : [] }))
  }

  function handleClassDrill(cls: string) {
    setDrillLevel('class')
    setDrillClass(cls)
    setActiveClass(cls)
    setFilter((f) => ({ ...f, classes: [cls] }))
  }

  function handleInspect(studentId: number) {
    setDrillLevel('student')
    setDrillStudent(studentId)
  }

  function handleBreadcrumb(level: DrillLevel) {
    setDrillLevel(level)
    if (level === 'overview') {
      setDrillClass(null)
      setDrillStudent(null)
      setActiveClass(null)
      setFilter((f) => ({ ...f, classes: [] }))
    } else if (level === 'class') {
      setDrillStudent(null)
    }
  }

  function handleAgentFilter(f: DashboardFilterEvent) {
    setFilter({ classes: f.classes, period: f.period, grade: '' })
    setActiveClass(f.classes[0] ?? null)
    if (f.view === 'class' && f.classes.length > 0) {
      setDrillLevel('class')
      setDrillClass(f.classes[0])
    } else if (f.view === 'overview') {
      setDrillLevel('overview')
      setDrillClass(null)
      setDrillStudent(null)
    }
  }

  const drillStudentName = drillStudent !== null
    ? atRisk.find((s) => s.student_id === drillStudent)?.name
    : undefined

  return (
    <div className="flex h-screen bg-snow">
      <Sidebar />

      <div className="flex-1 overflow-y-auto px-6 py-8 min-w-0">

        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <h2 className="font-serif text-2xl font-normal text-carbon">Attendance Dashboard</h2>
            {summary?.date_range && (
              <p className="text-xs text-pewter mt-1">
                {summary.date_range.from} — {summary.date_range.to}
              </p>
            )}
          </div>
          <button
            onClick={() => setPanel((p) => !p)}
            className={`text-sm rounded-[10px] px-4 py-2 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-link-blue focus-visible:ring-offset-2 ${
              panelOpen
                ? 'bg-arctic-mist text-carbon'
                : 'bg-fog border border-arctic-mist text-pewter hover:text-carbon hover:border-pewter'
            }`}
          >
            {panelOpen ? 'Close chat' : 'Ask Excelsis'}
          </button>
        </div>

        {/* Filter bar */}
        <div className="mb-6">
          <FilterBar filter={filter} classes={availableClasses} onChange={setFilter} />
        </div>

        {/* Breadcrumb */}
        <Breadcrumb
          drillLevel={drillLevel}
          drillClass={drillClass}
          drillStudent={drillStudent}
          studentName={drillStudentName}
          onNavigate={handleBreadcrumb}
        />

        {/* KPI row */}
        {summary && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <KpiCard
              label="Attendance rate"
              value={`${summary.overall_attendance_rate}%`}
              featured
            />
            <KpiCard
              label="Total absences"
              value={summary.total_absences.toLocaleString()}
            />
            <KpiCard
              label="At-risk students"
              value={String(atRisk.length)}
              sub={loading ? undefined : 'below 75%'}
            />
            <KpiCard
              label="Students"
              value={summary.unique_students.toLocaleString()}
            />
          </div>
        )}

        {/* Overview: 2×2 chart grid */}
        {drillLevel === 'overview' && (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-8">
            <div className="bg-fog border border-arctic-mist rounded-[10px] p-5">
              <p className="text-xs text-pewter uppercase tracking-widest mb-4">Attendance by class</p>
              <AttendanceByClassChart
                data={classStats}
                activeClass={activeClass}
                onClassClick={handleClassClick}
                onClassDrill={handleClassDrill}
                loading={loading}
              />
              <p className="text-xs text-pewter mt-2">Single-click to filter · Double-click to drill down</p>
            </div>

            <div className="bg-fog border border-arctic-mist rounded-[10px] p-5">
              <p className="text-xs text-pewter uppercase tracking-widest mb-4">Weekly trend</p>
              <WeeklyTrendChart data={weeklyStats} loading={loading} />
            </div>

            <div className="bg-fog border border-arctic-mist rounded-[10px] p-5">
              <p className="text-xs text-pewter uppercase tracking-widest mb-4">Status breakdown</p>
              <StatusDonutChart data={statusCounts} loading={loading} />
            </div>

            <div className="bg-fog border border-arctic-mist rounded-[10px] p-5">
              <p className="text-xs text-pewter uppercase tracking-widest mb-4">Attendance by day of week</p>
              <WeekdayBarChart data={dowStats} loading={loading} />
            </div>
          </div>
        )}

        {/* Drill-down panel */}
        <DrilldownPanel
          drillLevel={drillLevel}
          drillClass={drillClass}
          drillStudent={drillStudent}
          atRisk={atRisk}
          sparklines={sparklines}
          loading={loading}
          onInspect={handleInspect}
        />

      </div>

      {panelOpen && (
        <ChatPanel
          atRisk={atRisk}
          summary={summary}
          onClose={() => setPanel(false)}
          onDashboardFilter={handleAgentFilter}
        />
      )}
    </div>
  )
}
