
import ChatComposer from './ChatComposer'
import MessageList from './MessageList'
import { useChat } from './useChat'
import './index.css'

// Block 6: compose the UI; this component owns no transport logic.
const Chat = ({ displayName }: { displayName: string }) => {
  const { messages, isSending, error, send, createPlaylist, stop } = useChat()

  return (
    <section className="chat" aria-label="Playit music assistant">
      <header className="chat-header">
        <div>
          <p className="chat-eyebrow">YOUR MUSIC COMPANION</p>
          <h1>Welcome, {displayName}</h1>
        </div>
        <span className="chat-mode">{'API · streaming'}</span>
      </header>
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