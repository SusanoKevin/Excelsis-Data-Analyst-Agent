import { AtRiskStudent, AttendanceSummary } from '../types'

export function buildSuggestions(
  atRisk: AtRiskStudent[],
  summary: AttendanceSummary | null,
): string[] {
  const out: string[] = []

  if (atRisk.length > 0) {
    const worst = atRisk[0]
    const name = worst.name ?? `Student #${worst.student_id}`
    out.push(`Why is ${name} flagged as at risk?`)
  }

  if ((summary?.classes?.length ?? 0) > 0) {
    out.push('Which class has the lowest attendance this month?')
  }

  out.push('Show me the weekly attendance trend')
  out.push('What are the best intervention strategies for chronic absenteeism?')

  return out.slice(0, 4)
}
