export const METRIC_THRESHOLD = 75

export const C = {
  danger:  '#e74c3c',
  warning: '#f5a623',
  success: '#00a86b',
  link:    '#007aff',
  grid:    '#ececec',
  muted:   '#5d5d5d',
} as const

export function rateHex(rate: number): string {
  if (rate < 70) return C.danger
  if (rate < 80) return C.warning
  return C.success
}
