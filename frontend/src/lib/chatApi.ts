// Import geminiApi dependencies.
import { createGeminiInteraction, geminiApi } from './geminiApi'

// Describe the ConversationTurn data contract.
export type ConversationTurn = { role: 'user' | 'assistant'; text: string }

// Define getChatIntent as an async operation.
export async function getChatIntent(prompt: string, history: ConversationTurn[], signal: AbortSignal) {
  // Prepare { data } for the following operation.
  const { data } = await geminiApi.post<{ action: 'chat' | 'playlist' }>('/intent', { prompt, history }, { signal })
  // Check data.action !== 'chat' && data.action !== 'playlist'.
  if (data.action !== 'chat' && data.action !== 'playlist') throw new Error('Invalid conversation action.')
  // Return the current operation's result.
  return data.action
}

// Block 1: the UI consumes events, independently of the eventual LLM transport.
export type ChatEvent =
  | { type: 'status'; text: string }
  | { type: 'delta'; text: string }


// Keep the completed-response helper for existing consumers.
export async function requestChatResponse(prompt: string, signal: AbortSignal): Promise<string> {
  // Prepare response for the following operation.
  const response = await createGeminiInteraction({ prompt, signal })
  // Check typeof response.output !== 'string' || !response.output.trim().
  if (typeof response.output !== 'string' || !response.output.trim()) {
    // Reject invalid input or a failed operation.
    throw new Error('The server returned an empty or invalid response.')
  }
  // Return the current operation's result.
  return response.output
}

// Define streamChatResponse as an async operation.
export async function* streamChatResponse(
  prompt: string,
  signal: AbortSignal,
  history: ConversationTurn[] = [],
): AsyncGenerator<ChatEvent> {

  // Check !prompt.trim().
  if (!prompt.trim()) throw new Error('A valid prompt is required.')
  // Prepare response for the following operation.
  const response = await fetch(`${geminiApi.defaults.baseURL}/interactions/stream`, {
    // Set the method option/value.
    method: 'POST',
    // Set the headers option/value.
    headers: { 'Content-Type': 'application/json', Accept: 'application/x-ndjson' },
    // Set the credentials option/value.
    credentials: 'include',
    // Set the body option/value.
    body: JSON.stringify({ prompt, history }),
    signal,
  })
  // Check !response.ok || !response.body.
  if (!response.ok || !response.body) {
    await response.body?.cancel()
    // Reject invalid input or a failed operation.
    throw new Error(`Chat request failed (${response.status}).`)
  }
  // Prepare reader for the following operation.
  const reader = response.body.getReader()
  // Prepare decoder for the following operation.
  const decoder = new TextDecoder()
  // Prepare buffer for the following operation.
  let buffer = ''
  // Prepare receivedText for the following operation.
  let receivedText = false
  // Handle request failures and cleanup below.
  try {
    // Continue while true.
    while (true) {
      // Stop if the user cancelled this request.
      signal.throwIfAborted()
      // Prepare { value, done } for the following operation.
      const { value, done } = await reader.read()
      // Reads can split both JSON records and UTF-8 characters.
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true })
      // Prepare newline for the following operation.
      let newline = buffer.indexOf('\n')
      // Continue while newline !== -1.
      while (newline !== -1) {
        // Prepare line for the following operation.
        const line = buffer.slice(0, newline).trim()
        buffer = buffer.slice(newline + 1)
        // Check line.
        if (line) {
          // Prepare event for the following operation.
          const event: unknown = JSON.parse(line)
          // Check !event || typeof event !== 'object' || !('type' in event).
          if (!event || typeof event !== 'object' || !('type' in event)) {
            // Reject invalid input or a failed operation.
            throw new Error('Invalid stream event.')
          }
          // Check event.type === 'error'.
          if (event.type === 'error') throw new Error('Could not complete the response.')
          // Check event.type === 'done'.
          if (event.type === 'done') {
            // Check !receivedText.
            if (!receivedText) throw new Error('The response was empty.')
            // Return the current operation's result.
            return
          }
          // Check event.type === 'delta' || event.type === 'status'.
          if (event.type === 'delta' || event.type === 'status') {
            // Check !('text' in event) || typeof event.text !== 'string'.
            if (!('text' in event) || typeof event.text !== 'string') {
              // Reject invalid input or a failed operation.
              throw new Error('Invalid stream text.')
            }
            // Check event.type === 'delta' && event.text.
            if (event.type === 'delta' && event.text) receivedText = true
            yield { type: event.type, text: event.text }
          }
        }
        newline = buffer.indexOf('\n')
      }
      // Check done.
      if (done) throw new Error('The response stream ended before completion.')
    }
  } finally {
    // Call reader.cancel.
    await reader.cancel().catch(() => {})
    // Call reader.releaseLock.
    reader.releaseLock()
  }
}

/* File summary
 * - Requests validated intent or completed chat text.
 * - Parses streamed NDJSON status/text events across network chunks.
 * - Rejects malformed/incomplete streams and cleans up the reader.
 */
