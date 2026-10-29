// Use React state/lifecycle APIs.
import { useEffect, useRef, useState } from 'react'
// Import chatApi dependencies.
import { getChatIntent, streamChatResponse, type ConversationTurn } from '../../src/lib/chatApi'
import { approveAndCreatePlaylist, getPlaylistPreview, musicErrorMessage, preparePlaylist, runPlaylistAgent, type MusicProvider } from '../../src/lib/musicApi'
import type { ChatMessage } from './types'

// Describe the ChatMode data contract.
export type ChatMode = 'agent' | 'rest'
// Prepare CHAT_MODE_STORAGE_KEY for the following operation.
const CHAT_MODE_STORAGE_KEY = 'playit-chat-mode'

// Block 2: request lifecycle, cancellation, and API errors.
export function useChat(provider: MusicProvider = 'spotify') {
  // Track [messages, setMessages] in component state.
  const [messages, setMessages] = useState<ChatMessage[]>([])
  // Track [isSending, setIsSending] in component state.
  const [isSending, setIsSending] = useState(false)
  // Track [error, setError] in component state.
  const [error, setError] = useState<string | null>(null)
  // Track [mode, setMode] in component state.
  const [mode, setMode] = useState<ChatMode>(() => {
    // Handle request failures and cleanup below.
    try {
      // Return the current operation's result.
      return localStorage.getItem(CHAT_MODE_STORAGE_KEY) === 'rest' ? 'rest' : 'agent'
    } catch {
      // Return the current operation's result.
      return 'agent'
    }
  })
  // Keep controller across renders without triggering updates.
  const controller = useRef<AbortController | null>(null)
  // Keep creating across renders without triggering updates.
  const creating = useRef(new Set<string>())

  // Synchronize lifecycle work and return cleanup when needed.
  useEffect(() => () => controller.current?.abort(), [])

  // Define the selectMode handler/helper.
  const selectMode = (nextMode: ChatMode) => {
    // Call setMode.
    setMode(nextMode)
    // Handle request failures and cleanup below.
    try {
      // Persist the selected chat mode, not credentials.
      localStorage.setItem(CHAT_MODE_STORAGE_KEY, nextMode)
    } catch {
      // The selected mode remains available for this page if storage is disabled.
    }
  }

  // Create a cancellation signal for this request.
  const send = async (input: string) => {
    // Prepare prompt for the following operation.
    const prompt = input.trim()
    // Check !prompt || controller.current.
    if (!prompt || controller.current) return
    // Create a cancellation signal for this request.
    const request = new AbortController()
    controller.current = request
    // Call setIsSending.
    setIsSending(true)
    // Call setError.
    setError(null)
    // Prepare id for the following operation.
    const id = crypto.randomUUID()
    // Prepare requestMode for the following operation.
    const requestMode = mode
    // Send only completed user/model text, never preview tracks, tokens,
    // Spotify IDs, creation outcomes, progress events or partial/error replies.
    const history: ConversationTurn[] = []
    // Prepare historySize for the following operation.
    let historySize = 0
    // Process each entry in [...messages].reverse().
    for (const message of [...messages].reverse()) {
      // Check message.status !== 'complete'.
      if (message.status !== 'complete') continue
      // Prepare text for the following operation.
      const text = (message.contextText ?? message.text).slice(0, 10_000)
      // Check !text.trim().
      if (!text.trim()) continue
      // Check history.length >= 20 || historySize + text.length > 40_000.
      if (history.length >= 20 || historySize + text.length > 40_000) break
      // Call history.unshift.
      history.unshift({ role: message.role, text })
      historySize += text.length
    }
    // Call setMessages.
    setMessages((previous) => [...previous,
      { id: crypto.randomUUID(), role: 'user', text: prompt, progress: [], status: 'complete' },
      { id, role: 'assistant', text: '', progress: [], status: 'streaming' },
    ])

    // Define the update handler/helper.
    const update = (change: (message: ChatMessage) => ChatMessage) => {
      // Call setMessages.
      setMessages((previous) => previous.map((message) => message.id === id ? change(message) : message))
    }

    // Handle request failures and cleanup below.
    try {
      // Check requestMode === 'agent'.
      if (requestMode === 'agent') {
        // Call update.
        update((message) => ({ ...message, progress: ['Playit is considering your request and available actions…'] }))
        // Prepare result for the following operation.
        const result = await runPlaylistAgent(prompt, request.signal, history, provider)
        // Stop if the user cancelled this request.
        request.signal.throwIfAborted()
        // Call update.
        update((message) => ({
          ...message,
          // Set the text option/value.
          text: result.text,
          // Set the status option/value.
          status: 'complete',
          // Set the contextText option/value.
          contextText: result.contextText ?? undefined,
          ...(result.preview ? {
            // Set the playlist option/value.
            playlist: {
              // Set the preview option/value.
              preview: result.preview,
              // Set the creating option/value.
              creating: false,
              // Set the result option/value.
              result: result.preview.result,
              // Set the error option/value.
              error: null,
            },
          } : {}),
        }))
      } else {
        // Call update.
        update((message) => ({ ...message, progress: ['Understanding your request…'] }))
        // Prepare action for the following operation.
        const action = await getChatIntent(prompt, history, request.signal)
        // Stop if the user cancelled this request.
        request.signal.throwIfAborted()
        // Check action === 'playlist'.
        if (action === 'playlist') {
          // Prepare destination for the following operation.
          const destination = provider === 'youtube' ? 'YouTube' : 'Spotify'
          // Call update.
          update((message) => ({ ...message, text: `Finding recommendations and matching them on ${destination}…` }))
          // Prepare { preview, contextText } for the following operation.
          const { preview, contextText } = await preparePlaylist(prompt, request.signal, history, provider)
          // Stop if the user cancelled this request.
          request.signal.throwIfAborted()
          // Call update.
          update((message) => ({
            ...message,
            // Set the text option/value.
            text: `Here is your playlist preview. Review the matches below before creating it on ${destination}.`,
            // Set the status option/value.
            status: 'complete',
            contextText,
            // Set the playlist option/value.
            playlist: { preview, creating: false, result: preview.result, error: null },
          }))
        } else {
          // Process each entry in streamChatResponse(prompt, request.signal, history).
          for await (const event of streamChatResponse(prompt, request.signal, history)) {
            // Check request.signal.aborted.
            if (request.signal.aborted) break
            // Call update.
            update((message) => event.type === 'delta'
              ? { ...message, text: message.text + event.text }
              : { ...message, progress: [...message.progress, event.text] })
          }
          // Call update.
          update((message) => ({ ...message, status: request.signal.aborted ? 'stopped' : 'complete' }))
        }
      }
    } catch (err) {
      // Check request.signal.aborted.
      if (request.signal.aborted) {
        // Call update.
        update((message) => ({ ...message, status: 'stopped' }))
      } else {
        // Call setError.
        setError(musicErrorMessage(err))
        // Call update.
        update((message) => ({ ...message, status: 'error' }))
      }
    } finally {
      // Check controller.current === request.
      if (controller.current === request) {
        controller.current = null
        // Call setIsSending.
        setIsSending(false)
      }
    }
  }

  // Define the createPlaylist handler/helper.
  const createPlaylist = async (messageId: string) => {
    // Define the message handler/helper.
    const message = messages.find((item) => item.id === messageId)
    // Check !message?.playlist || message.playlist.result || creating.current.has(messageId).
    if (!message?.playlist || message.playlist.result || creating.current.has(messageId)) return
    // Prepare draftId for the following operation.
    const draftId = message.playlist.preview.draft_id
    // Call creating.current.add.
    creating.current.add(messageId)
    // Define the update handler/helper.
    const update = (change: Partial<NonNullable<ChatMessage['playlist']>>) => {
      // Call setMessages.
      setMessages((previous) => previous.map((item) => item.id === messageId && item.playlist
        ? { ...item, playlist: { ...item.playlist, ...change } } : item))
    }
    // Call update.
    update({ creating: true, error: null })
    // Handle request failures and cleanup below.
    try {
      // Call update.
      update({ result: await approveAndCreatePlaylist(draftId, message.playlist.preview.proposal.provider) })
    } catch (err) {
      // Call update.
      update({ error: musicErrorMessage(err) })
      // A failed response does not mean Spotify rejected the write. Read the
      // recorded outcome rather than submitting a fresh draft or retrying writes.
      try {
        // Prepare preview for the following operation.
        const preview = await getPlaylistPreview(draftId, message.playlist.preview.proposal.provider)
        // Call update.
        update({ result: preview.result })
      } catch { /* Preserve the original error; same-draft retries are server-guarded. */ }
    } finally {
      // Call creating.current.delete.
      creating.current.delete(messageId)
      // Call update.
      update({ creating: false })
    }
  }

  // Return the current operation's result.
  return { messages, isSending, error, mode, selectMode, send, createPlaylist, stop: () => controller.current?.abort() }
}

/* File summary
 * - Owns message history, cancellation, Agent/REST mode, and errors.
 * - Attaches real draft previews and preserves model-only context.
 * - Requires explicit approval and avoids blind creation retries.
 */
