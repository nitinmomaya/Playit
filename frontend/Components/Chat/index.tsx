
// Import ChatComposer dependencies.
import ChatComposer from './ChatComposer'
// Import MessageList dependencies.
import MessageList from './MessageList'
// Import useChat dependencies.
import { useChat } from './useChat'
// Import index.css dependencies.
import './index.css'

// Block 6: compose the UI; this component owns no transport logic.
const Chat = ({ displayName, provider = 'Spotify' }: { displayName: string; provider?: 'Spotify' | 'YouTube' }) => {
  // Keep display labels separate from the lowercase IDs used by musicApi.
  const musicProvider = provider === 'YouTube' ? 'youtube' : 'spotify'
  // Prepare { messages, isSending, error, mode, selectMode, send, createPlaylist, stop } for the following operation.
  const { messages, isSending, error, mode, selectMode, send, createPlaylist, stop } = useChat(musicProvider)

  // Return the current operation's result.
  return (
    // Render section.
    <section className="chat" aria-label="Playit music assistant">
      {/* Render header. */}
      <header className="chat-header">
        {/* Render div. */}
        <div>
          {/* Render p. */}
          <p className="chat-eyebrow">YOUR MUSIC COMPANION</p>
          {/* Render h1. */}
          <h1>Welcome, {displayName}</h1>
        </div>
        {/* Render div. */}
        <div className="chat-mode-picker" role="group" aria-label="Chat mode">
          {/* Render span. */}
          <span className="chat-mode-label">Mode</span>
          {/* Render button and handle onClick. */}
          <button type="button" className={mode === 'agent' ? 'is-selected' : ''}
            aria-pressed={mode === 'agent'} disabled={isSending} onClick={() => selectMode('agent')}>
            Agent
          </button>
          {/* Render button and handle onClick. */}
          <button type="button" className={mode === 'rest' ? 'is-selected' : ''}
            aria-pressed={mode === 'rest'} disabled={isSending} onClick={() => selectMode('rest')}>
            REST API
          </button>
        </div>
      </header>
      <p>{provider} · Review the matched songs, then approve to create your playlist.</p>
      {/* Render MessageList and handle onCreatePlaylist. */}
      <MessageList messages={messages} onCreatePlaylist={createPlaylist} />
      {/* Render p. */}
      <p className="chat-sr-only" role="status">
        {/* Render the matching state/condition only. */}
        {isSending ? 'Playit is responding.' : messages.length ? 'Response finished.' : ''}
      </p>
      {/* Render the matching state/condition only. */}
      {error && <p className="chat-error" role="alert">{error}</p>}
      {/* Render ChatComposer and handle onSend, onStop. */}
      <ChatComposer isSending={isSending} onSend={send} onStop={stop} />
    </section>
  )
}

// Export this module's public entry point.
export default Chat

/* File summary
 * - Composes messages, mode controls, errors, and the composer.
 * - Delegates request and playlist state to useChat.
 */
