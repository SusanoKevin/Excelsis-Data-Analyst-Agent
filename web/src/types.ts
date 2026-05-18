export interface AuthUser {
  token:  string
  userId: string
}

// ── Dashboard filter / drill state ────────────────────────────────────────────

export type DashboardPeriod = 'all' | 'last_7_days' | 'last_30_days' | 'custom'
export type DrillLevel      = 'overview' | 'class' | 'student'

export interface DashboardFilter {
  classes:    string[]
  period:     DashboardPeriod
  date_from?: string
  date_to?:   string
}

export interface DashboardFilterEvent {
  classes: string[]
  period:  DashboardPeriod
  view:    DrillLevel
}

// ── Chart data row shapes ─────────────────────────────────────────────────────

export interface ClassStat {
  class:           string
  total:           number
  present:         number
  absent:          number
  late:            number
  attendance_rate: number
}

export interface WeeklyStat {
  week:            string
  total:           number
  present:         number
  absent:          number
  late:            number
  attendance_rate: number
}

export interface DayOfWeekStat {
  day_of_week:     string
  total:           number
  present:         number
  absent:          number
  late:            number
  attendance_rate: number
}

export interface StatusCount {
  name:  string
  value: number
  color: string
}

// ── Messaging ─────────────────────────────────────────────────────────────────

export interface Message {
  role:             'user' | 'assistant'
  content:          string
  toolsUsed:        string[]
  isStreaming?:     boolean
  dashboardFilter?: DashboardFilterEvent
}

// ── API response shapes ───────────────────────────────────────────────────────

export interface AttendanceSummary {
  total_records:           number
  unique_students:         number
  date_range:              { from: string; to: string }
  overall_attendance_rate: number
  total_absences:          number
  classes:                 string[]
}

export interface StatsRow {
  [key: string]: string | number
  attendance_rate: number
}

export interface AtRiskStudent {
  student_id:      number
  name?:           string
  cls?:            string
  total:           number
  present:         number
  absent:          number
  late:            number
  attendance_rate: number
}

