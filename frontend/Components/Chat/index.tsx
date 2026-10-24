
import ChatComposer from './ChatComposer'
import MessageList from './MessageList'
import { useChat } from './useChat'
import './index.css'

// Block 6: compose the UI; this component owns no transport logic.
const Chat = ({ displayName, provider = 'Spotify' }: { displayName: string; provider?: 'Spotify' | 'YouTube' }) => {
  const { messages, isSending, error, mode, selectMode, send, createPlaylist, stop } = useChat(provider)

  return (
    <section className="chat" aria-label="Playit music assistant">
      <header className="chat-header">
        <div>
          <p className="chat-eyebrow">YOUR MUSIC COMPANION</p>
          <h1>Welcome, {displayName}</h1>
        </div>
        <div className="chat-mode-picker" role="group" aria-label="Chat mode">
          <span className="chat-mode-label">Mode</span>
          <button type="button" className={mode === 'agent' ? 'is-selected' : ''}
            aria-pressed={mode === 'agent'} disabled={isSending} onClick={() => selectMode('agent')}>
            Agent
          </button>
          <button type="button" className={mode === 'rest' ? 'is-selected' : ''}
            aria-pressed={mode === 'rest'} disabled={isSending} onClick={() => selectMode('rest')}>
            REST API
          </button>
        </div>
      </header>
      {<p>{`${provider} · Review the matched songs, then approve to create your playlist.`}</p>}
      <MessageList messages={messages} onCreatePlaylist={createPlaylist} />
      <p className="chat-sr-only" role="status">
        {isSending ? 'Playit is responding.' : messages.length ? 'Response finished.' : ''}
      </p>
      {error && <p className="chat-error" role="alert">{error}</p>}
      <ChatComposer isSending={isSending} onSend={send} onStop={stop} />
    </section>
  )
}

export default Chat