import { useEffect, useRef, useState } from 'react'
import { streamChatResponse } from '../../src/lib/chatApi'
import type { ChatMessage } from './types'

// Block 2: request lifecycle, incremental updates, cancellation, and API errors.
function waitForPaint(): Promise<void> {
  return new Promise((resolve) => {
    if (document.visibilityState === 'visible') {
      requestAnimationFrame(() => resolve())
    } else {
      window.setTimeout(resolve, 16)
    }
  })
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const controller = useRef<AbortController | null>(null)

  useEffect(() => () => controller.current?.abort(), [])

  const send = async (input: string) => {
    const prompt = input.trim()
    if (!prompt || controller.current) return
    const request = new AbortController()
    controller.current = request
    setIsSending(true)
    setError(null)
    const id = crypto.randomUUID()
    setMessages((previous) => [...previous,
      { id: crypto.randomUUID(), role: 'user', text: prompt, progress: [], status: 'complete' },
      { id, role: 'assistant', text: '', progress: [], status: 'streaming' },
    ])

    const update = (change: (message: ChatMessage) => ChatMessage) => {
      setMessages((previous) => previous.map((message) => message.id === id ? change(message) : message))
    }

    try {
      for await (const event of streamChatResponse(prompt, request.signal)) {
        if (request.signal.aborted) break
        update((message) => event.type === 'delta'
          ? { ...message, text: message.text + event.text }
          : { ...message, progress: [...message.progress, event.text] })
        // A single network read can contain many already-buffered records.
        // Let the browser paint each appended delta before consuming the next.
        if (event.type === 'delta') await waitForPaint()
      }
      update((message) => ({ ...message, status: request.signal.aborted ? 'stopped' : 'complete' }))
    } catch {
      if (request.signal.aborted) {
        update((message) => ({ ...message, status: 'stopped' }))
      } else {
        setError('Couldn’t get a response. Please try sending your message again.')
        update((message) => ({ ...message, status: 'error' }))
      }
    } finally {
      if (controller.current === request) {
        controller.current = null
        setIsSending(false)
      }
    }
  }

  return { messages, isSending, error, send, stop: () => controller.current?.abort() }
}