import { useEffect, useState } from 'react'
import api from '../api/client'
import {
  AttendanceSummary,
  AtRiskStudent,
  ClassStat,
  DashboardFilter,
  DayOfWeekStat,
  StatusCount,
  WeeklyStat,
} from '../types'

export interface DashboardData {
  summary:      AttendanceSummary | null
  classStats:   ClassStat[]
  weeklyStats:  WeeklyStat[]
  dowStats:     DayOfWeekStat[]
  statusCounts: StatusCount[]
  atRisk:       AtRiskStudent[]
  sparklines:   Record<string, (number | null)[]>
  loading:      boolean
  error:        string | null
}

const INITIAL: DashboardData = {
  summary:      null,
  classStats:   [],
  weeklyStats:  [],
  dowStats:     [],
  statusCounts: [],
  atRisk:       [],
  sparklines:   {},
  loading:      true,
  error:        null,
}

function deriveStatusCounts(classStats: ClassStat[]): StatusCount[] {
  const totals = classStats.reduce(
    (acc, row) => ({
      total:   acc.total   + row.total,
      present: acc.present + row.present,
      absent:  acc.absent  + row.absent,
      late:    acc.late    + row.late,
    }),
    { total: 0, present: 0, absent: 0, late: 0 }
  )
  const excused = Math.max(0, totals.total - totals.present - totals.absent - totals.late)
  return [
    { name: 'Present', value: totals.present, color: '#00a86b' },
    { name: 'Absent',  value: totals.absent,  color: '#e74c3c' },
    { name: 'Late',    value: totals.late,    color: '#f5a623' },
    ...(excused > 0 ? [{ name: 'Excused', value: excused, color: '#9b59b6' }] : []),
  ]
}

function buildParams(filter: DashboardFilter) {
  return {
    classes: filter.classes.join(','),
    period:  filter.period,
  }
}

export function useDashboardData(filter: DashboardFilter): DashboardData {
  const [data, setData] = useState<DashboardData>(INITIAL)

  const filterKey = `${filter.classes.join(',')}|${filter.period}|${filter.grade}`

  useEffect(() => {
    const controller = new AbortController()
    const { signal } = controller
    const params = buildParams(filter)

    setData((d) => ({ ...d, loading: true, error: null }))

    Promise.all([
      api.get('/data/summary',  { signal }),
      api.get('/data/stats',    { params: { ...params, group_by: 'class'       }, signal }),
      api.get('/data/stats',    { params: { ...params, group_by: 'week'        }, signal }),
      api.get('/data/stats',    { params: { ...params, group_by: 'day_of_week' }, signal }),
      api.get('/data/at-risk',  { params: { threshold: 75, classes: params.classes }, signal }),
    ])
      .then(([summaryRes, classRes, weekRes, dowRes, atRiskRes]) => {
        if (signal.aborted) return
        const atRisk: AtRiskStudent[] = atRiskRes.data
        const classStats: ClassStat[] = classRes.data

        setData({
          summary:      summaryRes.data,
          classStats,
          weeklyStats:  weekRes.data,
          dowStats:     dowRes.data,
          statusCounts: deriveStatusCounts(classStats),
          atRisk,
          sparklines:   {},
          loading:      false,
          error:        null,
        })

        if (atRisk.length > 0) {
          const ids = atRisk.map((s) => s.student_id).join(',')
          api.get(`/data/sparklines`, { params: { ids }, signal })
            .then((r) => {
              if (!signal.aborted)
                setData((d) => ({ ...d, sparklines: r.data }))
            })
            .catch(() => {})
        }
      })
      .catch((err) => {
        if (!signal.aborted)
          setData((d) => ({ ...d, loading: false, error: 'Failed to load dashboard data' }))
      })

    return () => controller.abort()
  }, [filterKey]) // eslint-disable-line react-hooks/exhaustive-deps

  return data
}
