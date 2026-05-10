import { KeyboardEvent, useEffect, useRef, useState } from 'react'
import Sidebar from '../components/Sidebar'
import MessageBubble from '../components/MessageBubble'
import { streamChat } from '../api/client'
import { Message } from '../types'

const SUGGESTIONS = [
  'Which classes have the lowest attendance this month?',
  'List at-risk students below 70%',
  'What are the best intervention strategies for chronic absenteeism?',
  'Show me the weekly attendance trend',
]

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput]       = useState('')
  const [streaming, setStreaming] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async (text: string) => {
    const q = text.trim()
    if (!q || streaming) return
    setInput('')
    setStreaming(true)

    // Add user message
    setMessages((prev) => [...prev, { role: 'user', content: q, toolsUsed: [] }])

    // Add empty streaming assistant message
    setMessages((prev) => [...prev, { role: 'assistant', content: '', toolsUsed: [], isStreaming: true }])

    const updateLast = (patch: object) =>
      setMessages((prev) => {
        const msgs = [...prev]
        msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], ...patch }
        return msgs
      })

    await streamChat(
      q,
      // onToken
      (token) => setMessages((prev) => {
        const msgs = [...prev]
        const last = msgs[msgs.length - 1]
        msgs[msgs.length - 1] = { ...last, content: last.content + token }
        return msgs
      }),
      // onToolStart
      (tool) => setMessages((prev) => {
        const msgs = [...prev]
        const last = msgs[msgs.length - 1]
        if (!last.toolsUsed.includes(tool))
          msgs[msgs.length - 1] = { ...last, toolsUsed: [...last.toolsUsed, tool] }
        return msgs
      }),
      // onToolEnd — no-op (pill stays)
      () => {},
      // onDone
      () => { updateLast({ isStreaming: false }); setStreaming(false) },
      // onError
      (msg) => { updateLast({ content: `⚠️ ${msg}`, isStreaming: false }); setStreaming(false) },
      // onRouting — LLaMA handed off to Qwen
      () => updateLast({ isRouting: true }),
      // onDashboard — Qwen generated a chart
      (url) => updateLast({ dashboardUrl: url }),
    )
  }

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send(input)
    }
  }

  return (
    <div className="flex h-screen">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="border-b border-border px-6 py-4">
          <h2 className="text-sm font-semibold text-white">Attendance Chat</h2>
          <p className="text-xs text-slate-500">Ask anything about attendance data in natural language</p>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center">
              <p className="text-slate-400 text-sm mb-6">Start by asking a question or try one of these:</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-xl">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="text-left text-xs text-slate-300 bg-surface border border-border hover:border-accent/60 hover:text-white rounded-xl px-4 py-3 transition-colors"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((m, i) => <MessageBubble key={i} msg={m} />)}
              <div ref={bottomRef} />
            </>
          )}
        </div>

        {/* Input bar */}
        <div className="border-t border-border px-6 py-4">
          <div className="flex items-end gap-3 bg-surface border border-border rounded-2xl px-4 py-3">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKey}
              disabled={streaming}
              rows={1}
              placeholder="Ask about attendance…"
              className="flex-1 bg-transparent text-sm text-white placeholder-slate-500 resize-none focus:outline-none max-h-32"
              style={{ lineHeight: '1.5' }}
            />
            <button
              onClick={() => send(input)}
              disabled={streaming || !input.trim()}
              className="bg-accent hover:bg-accent/80 disabled:opacity-40 text-white rounded-xl px-4 py-2 text-sm font-medium transition-colors flex-shrink-0"
            >
              {streaming ? '…' : 'Send'}
            </button>
          </div>
          <p className="text-xs text-slate-600 mt-2 text-center">Enter to send · Shift+Enter for newline</p>
        </div>
      </div>
    </div>
  )
}
