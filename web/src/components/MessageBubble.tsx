import { Message } from '../types'

const TOOL_LABELS: Record<string, string> = {
  query_attendance:     'Attendance data',
  get_at_risk_students: 'At-risk list',
  search_knowledge_base:'Knowledge base',
  get_summary:          'Summary',
  generate_dashboard:   'Dashboard',
}

interface Props { msg: Message }

export default function MessageBubble({ msg }: Props) {
  const isUser = msg.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-5`}>
      <div className={`max-w-[78%] ${isUser ? 'order-1' : 'order-2'}`}>

        {!isUser && msg.isRouting && (
          <div className="flex items-center gap-1.5 mb-2">
            <span className="text-xs text-pewter">analyst</span>
          </div>
        )}

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
          className={`px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
            isUser
              ? 'bg-carbon text-white rounded-2xl rounded-tr-sm'
              : 'bg-fog text-carbon rounded-2xl rounded-tl-sm border border-arctic-mist'
          } ${msg.isStreaming ? 'cursor-blink' : ''}`}
        >
          {msg.content || (msg.isStreaming
            ? (msg.isRouting ? 'Connecting to analyst…' : '')
            : '…'
          )}
        </div>

        {!isUser && msg.dashboardUrl && (
          <div className="mt-3">
            <iframe
              src={msg.dashboardUrl}
              title="Attendance dashboard"
              className="w-full border-0 block rounded-[10px]"
              style={{ height: "480px" }}
              sandbox="allow-scripts allow-same-origin"
            />
            <div className="flex justify-end py-1.5">
              <a
                href={msg.dashboardUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-pewter hover:text-carbon transition-colors rounded focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-link-blue"
              >
                Open full screen ↗
              </a>
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
