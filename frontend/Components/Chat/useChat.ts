import { useEffect, useRef, useState } from 'react'
import { getChatIntent, streamChatResponse, type ConversationTurn } from '../../src/lib/chatApi'
import { approveAndCreatePlaylist, getPlaylistPreview, musicErrorMessage, preparePlaylist } from '../../src/lib/musicApi'
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
  const creating = useRef(new Set<string>())

  useEffect(() => () => controller.current?.abort(), [])

  const send = async (input: string) => {
    const prompt = input.trim()
    if (!prompt || controller.current) return
    const request = new AbortController()
    controller.current = request
    setIsSending(true)
    setError(null)
    const id = crypto.randomUUID()
    // Send only completed user/model text, never preview tracks, tokens,
    // Spotify IDs, creation outcomes, progress events or partial/error replies.
    const history: ConversationTurn[] = []
    let historySize = 0
    for (const message of [...messages].reverse()) {
      if (message.status !== 'complete') continue
      const text = (message.contextText ?? message.text).slice(0, 10_000)
      if (!text.trim()) continue
      if (history.length >= 20 || historySize + text.length > 40_000) break
      history.unshift({ role: message.role, text })
      historySize += text.length
    }
    setMessages((previous) => [...previous,
      { id: crypto.randomUUID(), role: 'user', text: prompt, progress: [], status: 'complete' },
      { id, role: 'assistant', text: '', progress: [], status: 'streaming' },
    ])

    const update = (change: (message: ChatMessage) => ChatMessage) => {
      setMessages((previous) => previous.map((message) => message.id === id ? change(message) : message))
    }

    try {
      update((message) => ({ ...message, progress: ['Understanding your request…'] }))
      const action = await getChatIntent(prompt, history, request.signal)
      request.signal.throwIfAborted()
      if (action === 'playlist') {
        update((message) => ({ ...message, text: 'Finding recommendations and matching them on Spotify…' }))
        const { preview, contextText } = await preparePlaylist(prompt, request.signal, history)
        request.signal.throwIfAborted()
        update((message) => ({
          ...message,
          text: 'Here is your playlist preview. Review the matches below before creating it on Spotify.',
          status: 'complete',
          contextText,
          playlist: { preview, creating: false, result: preview.result, error: null },
        }))
        return
      }
      for await (const event of streamChatResponse(prompt, request.signal, history)) {
        if (request.signal.aborted) break
        update((message) => event.type === 'delta'
          ? { ...message, text: message.text + event.text }
          : { ...message, progress: [...message.progress, event.text] })
        // A single network read can contain many already-buffered records.
        // Let the browser paint each appended delta before consuming the next.
        if (event.type === 'delta') await waitForPaint()
      }
      update((message) => ({ ...message, status: request.signal.aborted ? 'stopped' : 'complete' }))
    } catch (err) {
      if (request.signal.aborted) {
        update((message) => ({ ...message, status: 'stopped' }))
      } else {
        setError(musicErrorMessage(err))
        update((message) => ({ ...message, status: 'error' }))
      }
    } finally {
      if (controller.current === request) {
        controller.current = null
        setIsSending(false)
      }
    }
  }

  const createPlaylist = async (messageId: string) => {
    const message = messages.find((item) => item.id === messageId)
    if (!message?.playlist || message.playlist.result || creating.current.has(messageId)) return
    const draftId = message.playlist.preview.draft_id
    creating.current.add(messageId)
    const update = (change: Partial<NonNullable<ChatMessage['playlist']>>) => {
      setMessages((previous) => previous.map((item) => item.id === messageId && item.playlist
        ? { ...item, playlist: { ...item.playlist, ...change } } : item))
    }
    update({ creating: true, error: null })
    try {
      update({ result: await approveAndCreatePlaylist(draftId) })
    } catch (err) {
      update({ error: musicErrorMessage(err) })
      // A failed response does not mean Spotify rejected the write. Read the
      // recorded outcome rather than submitting a fresh draft or retrying writes.
      try {
        const preview = await getPlaylistPreview(draftId)
        update({ result: preview.result })
      } catch { /* Preserve the original error; same-draft retries are server-guarded. */ }
    } finally {
      creating.current.delete(messageId)
      update({ creating: false })
    }
  }

  return { messages, isSending, error, send, createPlaylist, stop: () => controller.current?.abort() }
}