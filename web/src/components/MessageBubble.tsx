import { Message } from '../types'

const TOOL_LABELS: Record<string, string> = {
  query_attendance:     'Attendance data',
  get_at_risk_students: 'At-risk list',
  search_knowledge_base:'Knowledge base',
  get_summary:          'Summary',
  web_search:           'Web search',
  generate_dashboard:   'Dashboard',
}

interface Props { msg: Message }

export default function MessageBubble({ msg }: Props) {
  const isUser = msg.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`max-w-[78%] ${isUser ? 'order-1' : 'order-2'}`}>

        {/* Routing badge — shown when LLaMA handed off to Qwen */}
        {!isUser && msg.isRouting && (
          <div className="flex items-center gap-1.5 mb-2">
            <span className="text-xs px-2 py-0.5 rounded-full bg-purple-900/50 border border-purple-500/40 text-purple-300">
              ⚡ Analyst
            </span>
          </div>
        )}

        {/* Tool-use pills (assistant only) */}
        {!isUser && msg.toolsUsed.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {msg.toolsUsed.map((t, i) => (
              <span
                key={i}
                className="text-xs px-2 py-0.5 rounded-full bg-navy/60 border border-accent/40 text-accent"
              >
                🔧 {TOOL_LABELS[t] ?? t}
              </span>
            ))}
          </div>
        )}

        {/* Bubble */}
        <div
          className={`px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
            isUser
              ? 'bg-accent text-white rounded-tr-sm'
              : 'bg-surface text-slate-200 rounded-tl-sm'
          } ${msg.isStreaming ? 'cursor-blink' : ''}`}
        >
          {msg.content || (msg.isStreaming
            ? (msg.isRouting ? '⚡ Connecting to analyst…' : '')
            : '…'
          )}
        </div>

        {/* Dashboard image — shown when Qwen called generate_dashboard */}
        {!isUser && msg.dashboardUrl && (
          <div className="mt-3">
            <a
              href={msg.dashboardUrl}
              target="_blank"
              rel="noopener noreferrer"
              title="Open full size"
            >
              <img
                src={msg.dashboardUrl}
                alt="Attendance dashboard"
                className="rounded-xl border border-border w-full hover:opacity-90 transition-opacity cursor-zoom-in"
              />
            </a>
            <p className="text-xs text-slate-500 mt-1">Click to open full size</p>
          </div>
        )}

      </div>
    </div>
  )
}
