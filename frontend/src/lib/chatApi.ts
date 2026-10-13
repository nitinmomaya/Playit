import { createGeminiInteraction, geminiApi } from './geminiApi'

// Block 1: the UI consumes events, independently of the eventual LLM transport.
export type ChatEvent =
  | { type: 'status'; text: string }
  | { type: 'delta'; text: string }


// Keep the completed-response helper for existing consumers.
export async function requestChatResponse(prompt: string, signal: AbortSignal): Promise<string> {
  const response = await createGeminiInteraction({ prompt, signal })
  if (typeof response.output !== 'string' || !response.output.trim()) {
    throw new Error('The server returned an empty or invalid response.')
  }
  return response.output
}

export async function* streamChatResponse(
  prompt: string,
  signal: AbortSignal,
): AsyncGenerator<ChatEvent> {

  if (!prompt.trim()) throw new Error('A valid prompt is required.')
  const response = await fetch(`${geminiApi.defaults.baseURL}/interactions/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/x-ndjson' },
    credentials: 'include',
    body: JSON.stringify({ prompt }),
    signal,
  })
  if (!response.ok || !response.body) {
    await response.body?.cancel()
    throw new Error(`Chat request failed (${response.status}).`)
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let receivedText = false
  try {
    while (true) {
      signal.throwIfAborted()
      const { value, done } = await reader.read()
      // Reads can split both JSON records and UTF-8 characters.
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true })
      let newline = buffer.indexOf('\n')
      while (newline !== -1) {
        const line = buffer.slice(0, newline).trim()
        buffer = buffer.slice(newline + 1)
        if (line) {
          const event: unknown = JSON.parse(line)
          if (!event || typeof event !== 'object' || !('type' in event)) {
            throw new Error('Invalid stream event.')
          }
          if (event.type === 'error') throw new Error('Could not complete the response.')
          if (event.type === 'done') {
            if (!receivedText) throw new Error('The response was empty.')
            return
          }
          if (event.type === 'delta' || event.type === 'status') {
            if (!('text' in event) || typeof event.text !== 'string') {
              throw new Error('Invalid stream text.')
            }
            if (event.type === 'delta' && event.text) receivedText = true
            yield { type: event.type, text: event.text }
          }
        }
        newline = buffer.indexOf('\n')
      }
      if (done) throw new Error('The response stream ended before completion.')
    }
  } finally {
    await reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}