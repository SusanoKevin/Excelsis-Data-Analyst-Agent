import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { DashboardFilterEvent, Message, ToolTable } from '../types'

const TOOL_LABELS: Record<string, string> = {
  query_data:            'Querying data…',
  get_threshold_alerts:  'Finding threshold alerts…',
  get_summary:           'Summary',
  update_dashboard_view: 'Dashboard filter',
  run_sql_query:         'SQL query',
  compare_periods:       'Period comparison',
  compare_segments:      'Comparing segments…',
  retrieve_schema:       'Looking up schema…',
  retrieve_policy:       'Retrieving policy…',
  statistical_summary:   'Computing statistics…',
  detect_anomalies:      'Detecting anomalies…',
  get_top_n:             'Ranking groups…',
  analyze_trend:         'Analysing trend…',
}

function DataTable({ table }: { table: ToolTable }) {
  return (
    <div className="mt-3 overflow-x-auto rounded-[10px] border border-arctic-mist text-xs">
      <table className="w-full text-left">
        <thead className="bg-fog">
          <tr>
            {table.columns.map((col) => (
              <th key={col} className="px-3 py-2 text-pewter uppercase tracking-wider font-medium whitespace-nowrap">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, i) => (
            <tr key={i} className={i % 2 === 0 ? 'bg-snow' : 'bg-fog'}>
              {row.map((cell, j) => (
                <td key={j} className="px-3 py-2 text-carbon font-mono whitespace-nowrap">
                  {cell === null || cell === undefined ? '' : String(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {table.truncated && (
        <p className="px-3 py-2 text-pewter border-t border-arctic-mist">
          Showing 50 of {table.total_rows} rows
        </p>
      )}
    </div>
  )
}

function buildDashboardUrl(f: DashboardFilterEvent): string {
  const params = new URLSearchParams()
  if (f.classes.length > 0) params.set('classes', f.classes.join(','))
  if (f.period !== 'all') params.set('period', f.period)
  if (f.view === 'group') params.set('view', f.view)
  const qs = params.toString()
  return `/dashboard${qs ? `?${qs}` : ''}`
}

interface Props { msg: Message }

export default function MessageBubble({ msg }: Props) {
  const isUser = msg.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-5`}>
      <div className={`max-w-[78%] ${isUser ? 'order-1' : 'order-2'}`}>

        {!isUser && msg.toolsUsed.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {msg.toolsUsed.map((t, i) => (
              <span
                key={i}
                className="text-xs px-2.5 py-0.5 rounded-pill border border-arctic-mist text-pewter bg-fog"
              >
                {TOOL_LABELS[t] ?? t}
              </span>
            ))}
          </div>
        )}

        <div
          className={`px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? 'bg-carbon text-white rounded-2xl rounded-tr-sm whitespace-pre-wrap'
              : 'bg-fog text-carbon rounded-2xl rounded-tl-sm border border-arctic-mist'
          } ${msg.isStreaming ? 'cursor-blink' : ''}`}
        >
          {isUser ? (
            msg.content || ''
          ) : (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                table: ({ children }) => (
                  <div className="overflow-x-auto rounded-[10px] border border-arctic-mist text-xs my-2">
                    <table className="w-full text-left">{children}</table>
                  </div>
                ),
                thead: ({ children }) => <thead className="bg-arctic-mist">{children}</thead>,
                th: ({ children }) => (
                  <th className="px-3 py-2 text-pewter uppercase tracking-wider font-medium whitespace-nowrap">
                    {children}
                  </th>
                ),
                td: ({ children }) => (
                  <td className="px-3 py-2 text-carbon font-mono whitespace-nowrap border-t border-arctic-mist">
                    {children}
                  </td>
                ),
                code: ({ children }) => (
                  <code className="bg-arctic-mist text-carbon font-mono text-xs px-1.5 py-0.5 rounded">
                    {children}
                  </code>
                ),
                p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
              }}
            >
              {msg.content || (msg.isStreaming ? '' : '…')}
            </ReactMarkdown>
          )}
        </div>

        {!isUser && msg.toolData && msg.toolData.length > 0 && (
          <div>
            {msg.toolData.map((t, i) => <DataTable key={i} table={t} />)}
          </div>
        )}

        {!isUser && msg.dashboardFilter && (
          <div className="mt-3">
            <a
              href={buildDashboardUrl(msg.dashboardFilter)}
              className="inline-flex items-center gap-2 text-sm bg-fog border border-arctic-mist hover:border-pewter text-carbon rounded-[10px] px-4 py-2 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-link-blue"
            >
              View in Dashboard ↗
            </a>
          </div>
        )}

      </div>
    </div>
  )
}
