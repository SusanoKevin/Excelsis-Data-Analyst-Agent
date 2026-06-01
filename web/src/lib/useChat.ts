import { useEffect, useState } from 'react'
import { streamChat } from '../api/client'
import { DashboardFilterEvent, Message } from '../types'

const STORAGE_KEY = 'excelsis_data_chat'

function loadHistory(): Message[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function useChat(onDashboardFilter?: (f: DashboardFilterEvent) => void) {
  const [messages, setMessages] = useState<Message[]>(loadHistory)
  const [streaming, setStreaming] = useState(false)

  useEffect(() => {
    try {
      const toSave = messages.map((m) => ({ ...m, isStreaming: false }))
      localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave))
    } catch {
      // localStorage full — ignore
    }
  }, [messages])

  const updateLast = (patch: Partial<Message> | ((m: Message) => Partial<Message>)) =>
    setMessages((prev) => {
      const msgs = [...prev]
      const last = msgs[msgs.length - 1]
      msgs[msgs.length - 1] = { ...last, ...(typeof patch === 'function' ? patch(last) : patch) }
      return msgs
    })

  const send = async (q: string) => {
    if (!q.trim() || streaming) return
    setStreaming(true)
    setMessages((prev) => [...prev, { role: 'user', content: q, toolsUsed: [] }])
    setMessages((prev) => [...prev, { role: 'assistant', content: '', toolsUsed: [], isStreaming: true }])

    await streamChat(
      q,
      (token) => updateLast((m) => ({ content: m.content + token })),
      (tool)  => updateLast((m) => m.toolsUsed.includes(tool) ? {} : { toolsUsed: [...m.toolsUsed, tool] }),
      () => {},
      () => { updateLast({ isStreaming: false }); setStreaming(false) },
      (msg) => { updateLast({ content: msg, isStreaming: false }); setStreaming(false) },
      (f) => { updateLast({ dashboardFilter: f }); onDashboardFilter?.(f) },
      (table) => updateLast((m) => ({ toolData: [...(m.toolData ?? []), table] })),
    )
  }

  const clearHistory = () => {
    setMessages([])
    localStorage.removeItem(STORAGE_KEY)
  }

  return { messages, streaming, send, clearHistory }
}
