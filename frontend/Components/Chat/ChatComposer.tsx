// Use React state/lifecycle APIs.
import { useState } from 'react'

// Describe the Props data contract.
type Props = { isSending: boolean; onSend: (input: string) => Promise<void>; onStop: () => void }

// Block 5: submit with the button or Enter; Shift+Enter adds a new line.
const ChatComposer = ({ isSending, onSend, onStop }: Props) => {
  // Track [input, setInput] in component state.
  const [input, setInput] = useState('')
  // Define the submit handler/helper.
  const submit = () => {
    // Check !input.trim() || isSending.
    if (!input.trim() || isSending) return
    // Call onSend.
    void onSend(input)
    // Call setInput.
    setInput('')
  }

  // Return the current operation's result.
  return (
    // Render form and handle onSubmit.
    <form className="chat-composer" onSubmit={(event) => { event.preventDefault(); submit() }}>
      {/* Render label. */}
      <label htmlFor="chat-prompt" className="chat-input-label">Message Playit</label>
      {/* Render div. */}
      <div className="chat-input-row">
        {/* Render textarea and handle onChange, onKeyDown. */}
        <textarea id="chat-prompt" value={input} rows={2} maxLength={4000}
          placeholder="Ask for songs, describe a playlist, or refine your last mix…"
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            // Check event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing.
            if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
              // Prevent the browser's default form/key action.
              event.preventDefault()
              // Call submit.
              submit()
            }
          }} />
        {/* Render the matching state/condition only. */}
        {isSending ? (
          // Render button and handle onClick.
          <button type="button" onClick={onStop}>Stop</button>
        ) : (
          // Render button.
          <button type="submit" disabled={!input.trim()}>
            Send <span aria-hidden="true">↑</span>
          </button>
        )}
      </div>
      {/* Render p. */}
      <p className="chat-composer-hint">
        Enter to send · Shift + Enter for a new line · Playlists are previewed before creation
      </p>
    </form>
  )
}

// Export this module's public entry point.
export default ChatComposer

/* File summary
 * - Tracks unsent text and submits nonblank input.
 * - Supports Enter, Shift+Enter, and a Stop control.
 * - Leaves API requests to the parent hook.
 */
