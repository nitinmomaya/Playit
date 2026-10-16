import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import ThinkingIndicator from './ThinkingIndicator'
import type { ChatMessage } from './types'

// Block 4: render assistant Markdown safely; raw HTML is not enabled.
const MessageList = ({ messages, onCreatePlaylist }: {
  messages: ChatMessage[]
  onCreatePlaylist: (messageId: string) => Promise<void>
}) => {
  const list = useRef<HTMLDivElement>(null)
  const followLatest = useRef(true)

  useEffect(() => {
    if (followLatest.current && list.current) {
      list.current.scrollTop = list.current.scrollHeight
    }
  }, [messages])

  return (
    <div className="chat-messages" ref={list} role="region" aria-label="Conversation"
      onScroll={() => {
        const element = list.current
        if (element) followLatest.current = element.scrollHeight - element.scrollTop - element.clientHeight < 80
      }}>
      {messages.length === 0 ? (
        <div className="chat-empty">
          <span className="chat-empty-icon" aria-hidden="true">♫</span>
          <h2>Your next playlist starts here</h2>
          <p>Tell Playit what you’re in the mood for. A late-night drive, old-school hits, or something new?</p>
        </div>
      ) : messages.map((message) => (
        <article key={message.id} className={`chat-message chat-message--${message.role}`}>
          <p className="chat-message-author">{message.role === 'user' ? 'You' : 'Playit'}</p>
          {message.role === 'assistant' && <ThinkingIndicator message={message} />}
          {message.role === 'assistant' && message.status === 'streaming' && !message.text && (
            <p className="chat-first-token" role="status">
              <span className="chat-pulse" aria-hidden="true" />
              Connecting to Gemini and waiting for the first token…
            </p>
          )}
          {message.text && (message.role === 'assistant' ? (
            <div className="chat-markdown">
              <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml
                components={{
                  // Do not load externally supplied images from model output.
                  img: ({ alt }) => <span>{alt}</span>,
                  a: ({ href, children }) => (
                    <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>
                  ),
                }}>
                {message.text}
              </ReactMarkdown>
            </div>
          ) : <p className="chat-message-text">{message.text}</p>)}
          {message.playlist && (
            <div className="chat-playlist-preview">
              <h3>{message.playlist.preview.proposal.name}</h3>
              <p>{message.playlist.preview.proposal.description}</p>
              <p>{message.playlist.preview.proposal.public ? 'Public' : 'Private'} · {message.playlist.preview.matched_count} unique tracks matched</p>
              {message.playlist.preview.total_duration_ms > 0 && <p>
                Listening time: {Math.floor(message.playlist.preview.total_duration_ms / 60000)} min {Math.round(message.playlist.preview.total_duration_ms % 60000 / 1000)} sec
              </p>}
              {message.playlist.preview.constraint_warning && <p className="chat-error" role="alert">{message.playlist.preview.constraint_warning}</p>}
              <ul>{message.playlist.preview.matches.map((match, index) => (
                <li key={index}>
                  <strong>{match.track?.title ?? match.recommendation.title}</strong>
                  {' — '}{match.track?.artists.join(', ') ?? match.recommendation.artist}
                  <span className="chat-message-note"> · {match.status.replaceAll('_', ' ')}</span>
                </li>
              ))}</ul>
              <p className="chat-message-note">The first best match is selected. Unmatched and duplicate suggestions are skipped.</p>
              {message.playlist.error && <p className="chat-error" role="alert">{message.playlist.error}</p>}
              {message.playlist.result ? (
                <p role="status">
                  {message.playlist.result.status === 'complete'
                    ? `Playlist created with ${message.playlist.result.added} ${message.playlist.result.added === 1 ? 'track' : 'tracks'}. `
                    : `Creation needs review (${message.playlist.result.added}/${message.playlist.result.total} confirmed). Check Spotify before making another playlist. `}
                  {message.playlist.result.url && <a href={message.playlist.result.url} target="_blank" rel="noopener noreferrer">Open in Spotify</a>}
                </p>
              ) : (
                <button type="button" disabled={message.playlist.creating || !message.playlist.preview.matched_count || !!message.playlist.preview.constraint_warning}
                  onClick={() => void onCreatePlaylist(message.id)}>
                  {message.playlist.creating ? 'Creating playlist…' : 'Approve and create on Spotify'}
                </button>
              )}
            </div>
          )}
          {message.status === 'stopped' && <p className="chat-message-note">Response stopped.</p>}
          {message.status === 'error' && <p className="chat-message-note">Response unavailable.</p>}
        </article>
      ))}
    </div>
  )
}

export default MessageList