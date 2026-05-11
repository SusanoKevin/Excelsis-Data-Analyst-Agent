export interface AuthUser {
  token: string
  role: string
  userId: string
  allowedClasses: string[]
}

export interface Message {
  role: 'user' | 'assistant'
  content: string
  toolsUsed: string[]
  isStreaming?: boolean
  isRouting?: boolean
  dashboardUrl?: string
}

export interface AttendanceSummary {
  total_records: number
  unique_students: number
  date_range: { from: string; to: string }
  overall_attendance_rate: number
  total_absences: number
  classes: string[]
}

export interface StatsRow {
  [key: string]: string | number
  attendance_rate: number
}

export interface AtRiskStudent {
  student_id: number
  name?: string
  cls?: string
  total: number
  present: number
  absent: number
  late: number
  attendance_rate: number
}

export interface UserRecord {
  username: string
  role: string
  allowed_classes: string[]
}
