import { useState } from 'react'
import { streamChat } from '../api/client'
import { Message } from '../types'

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [streaming, setStreaming] = useState(false)

  const updateLast = (patch: Partial<Message>) =>
    setMessages((prev) => {
      const msgs = [...prev]
      msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], ...patch }
      return msgs
    })

  const send = async (q: string) => {
    if (!q.trim() || streaming) return
    setStreaming(true)
    setMessages((prev) => [...prev, { role: 'user', content: q, toolsUsed: [] }])
    setMessages((prev) => [...prev, { role: 'assistant', content: '', toolsUsed: [], isStreaming: true }])

    await streamChat(
      q,
      (token) => setMessages((prev) => {
        const msgs = [...prev]
        const last = msgs[msgs.length - 1]
        msgs[msgs.length - 1] = { ...last, content: last.content + token }
        return msgs
      }),
      (tool) => setMessages((prev) => {
        const msgs = [...prev]
        const last = msgs[msgs.length - 1]
        if (!last.toolsUsed.includes(tool))
          msgs[msgs.length - 1] = { ...last, toolsUsed: [...last.toolsUsed, tool] }
        return msgs
      }),
      () => {},
      () => { updateLast({ isStreaming: false }); setStreaming(false) },
      (msg) => { updateLast({ content: msg, isStreaming: false }); setStreaming(false) },
      () => updateLast({ isRouting: true }),
      (url) => updateLast({ dashboardUrl: url }),
    )
  }

  return { messages, streaming, send }
}
