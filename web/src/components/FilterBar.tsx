import { useEffect, useRef, useState } from 'react'
import { DashboardFilter, DashboardPeriod } from '../types'

interface Props {
  filter:   DashboardFilter
  classes:  string[]
  onChange: (f: DashboardFilter) => void
}

const PERIODS: { value: DashboardPeriod; label: string }[] = [
  { value: 'all',          label: 'All time' },
  { value: 'last_30_days', label: 'Last 30 days' },
  { value: 'last_7_days',  label: 'Last 7 days' },
]

export default function FilterBar({ filter, classes, onChange }: Props) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  function toggleClass(cls: string) {
    const next = filter.classes.includes(cls)
      ? filter.classes.filter((c) => c !== cls)
      : [...filter.classes, cls]
    onChange({ ...filter, classes: next })
  }

  const isDefault = filter.classes.length === 0 && filter.period === 'all' && filter.grade === ''

  return (
    <div className="flex items-center gap-3 flex-wrap">
      <div className="relative" ref={ref}>
        <button
          onClick={() => setOpen((o) => !o)}
          className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-[10px] border border-arctic-mist bg-fog text-carbon hover:border-pewter transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-link-blue"
        >
          {filter.classes.length === 0 ? 'All classes' : filter.classes.join(', ')}
          <svg width="10" height="6" viewBox="0 0 10 6" fill="none" className={`flex-shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}>
            <path d="M1 1l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>

        {open && classes.length > 0 && (
          <div
            role="listbox"
            aria-multiselectable="true"
            aria-label="Select classes"
            className="absolute z-20 top-full mt-1 min-w-[160px] bg-fog border border-arctic-mist rounded-[10px] shadow-sm py-1 max-h-60 overflow-y-auto"
          >
            {classes.map((cls) => {
              const selected = filter.classes.includes(cls)
              return (
                <div
                  key={cls}
                  role="option"
                  aria-selected={selected}
                  tabIndex={0}
                  onClick={() => toggleClass(cls)}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleClass(cls) } }}
                  className={`flex items-center gap-2 px-3 py-2 text-sm cursor-pointer select-none transition-colors ${
                    selected ? 'text-carbon font-medium' : 'text-pewter hover:text-carbon hover:bg-arctic-mist'
                  }`}
                >
                  <span className={`w-3.5 h-3.5 rounded border flex-shrink-0 flex items-center justify-center ${selected ? 'bg-carbon border-carbon' : 'border-pewter'}`}>
                    {selected && (
                      <svg width="8" height="6" viewBox="0 0 8 6" fill="none">
                        <path d="M1 3l2 2 4-4" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    )}
                  </span>
                  {cls}
                </div>
              )
            })}
          </div>
        )}
      </div>

      <select
        value={filter.period}
        onChange={(e) => onChange({ ...filter, period: e.target.value as DashboardPeriod })}
        className="text-sm px-3 py-1.5 rounded-[10px] border border-arctic-mist bg-fog text-carbon hover:border-pewter transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-link-blue"
      >
        {PERIODS.map((p) => (
          <option key={p.value} value={p.value}>{p.label}</option>
        ))}
      </select>

      <input
        type="text"
        value={filter.grade}
        onChange={(e) => onChange({ ...filter, grade: e.target.value })}
        placeholder="Grade…"
        className="text-sm px-3 py-1.5 rounded-[10px] border border-arctic-mist bg-fog text-carbon placeholder-pewter w-24 hover:border-pewter transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-link-blue"
      />

      {!isDefault && (
        <button
          onClick={() => onChange({ classes: [], period: 'all', grade: '' })}
          className="text-xs text-pewter hover:text-carbon transition-colors underline-offset-2 hover:underline rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-link-blue"
        >
          Clear filters
        </button>
      )}
    </div>
  )
}
