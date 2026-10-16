import { useState } from 'react'

type Props = { isSending: boolean; onSend: (input: string) => Promise<void>; onStop: () => void }

// Block 5: submit with the button or Enter; Shift+Enter adds a new line.
const ChatComposer = ({ isSending, onSend, onStop }: Props) => {
  const [input, setInput] = useState('')
  const submit = () => {
    if (!input.trim() || isSending) return
    void onSend(input)
    setInput('')
  }

  return (
    <form className="chat-composer" onSubmit={(event) => { event.preventDefault(); submit() }}>
      <label htmlFor="chat-prompt" className="chat-input-label">Message Playit</label>
      <div className="chat-input-row">
        <textarea id="chat-prompt" value={input} rows={2} maxLength={4000}
          placeholder="Ask for songs, describe a playlist, or refine your last mix…"
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault()
              submit()
            }
          }} />
        {isSending ? (
          <button type="button" onClick={onStop}>Stop</button>
        ) : (
          <button type="submit" disabled={!input.trim()}>
            Send <span aria-hidden="true">↑</span>
          </button>
        )}
      </div>
      <p className="chat-composer-hint">
        Enter to send · Shift + Enter for a new line · Playlists are previewed before creation
      </p>
    </form>
  )
}

export default ChatComposer