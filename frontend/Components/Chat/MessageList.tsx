// Use React state/lifecycle APIs.
import { useEffect, useRef } from 'react'
// Render assistant Markdown without raw HTML.
import ReactMarkdown from 'react-markdown'
// Enable GitHub-flavored Markdown features.
import remarkGfm from 'remark-gfm'
// Import ThinkingIndicator dependencies.
import ThinkingIndicator from './ThinkingIndicator'
// Import types dependencies.
import type { ChatMessage } from './types'

// Block 4: render assistant Markdown safely; raw HTML is not enabled.
const MessageList = ({ messages, onCreatePlaylist }: {
  // Define messages in this data shape.
  messages: ChatMessage[]
  // Define onCreatePlaylist in this data shape.
  onCreatePlaylist: (messageId: string) => Promise<void>
}) => {
  // Keep list across renders without triggering updates.
  const list = useRef<HTMLDivElement>(null)
  // Keep followLatest across renders without triggering updates.
  const followLatest = useRef(true)

  // Synchronize lifecycle work and return cleanup when needed.
  useEffect(() => {
    // Check followLatest.current && list.current.
    if (followLatest.current && list.current) {
      list.current.scrollTop = list.current.scrollHeight
    }
  }, [messages])

  // Return the current operation's result.
  return (
    // Render div and handle onScroll.
    <div className="chat-messages" ref={list} role="region" aria-label="Conversation"
      onScroll={() => {
        // Prepare element for the following operation.
        const element = list.current
        // Check element.
        if (element) followLatest.current = element.scrollHeight - element.scrollTop - element.clientHeight < 80
      }}>
      {/* Render one entry for each item. */}
      {messages.length === 0 ? (
        // Render div.
        <div className="chat-empty">
          {/* Render span. */}
          <span className="chat-empty-icon" aria-hidden="true">♫</span>
          {/* Render h2. */}
          <h2>Your next playlist starts here</h2>
          {/* Render p. */}
          <p>Tell Playit what you’re in the mood for. A late-night drive, old-school hits, or something new?</p>
        </div>
      ) : messages.map((message) => (
        // Render article.
        <article key={message.id} className={`chat-message chat-message--${message.role}`}>
          {/* Render p. */}
          <p className="chat-message-author">{message.role === 'user' ? 'You' : 'Playit'}</p>
          {/* Render the matching state/condition only. */}
          {message.role === 'assistant' && <ThinkingIndicator message={message} />}
          {/* Render the matching state/condition only. */}
          {message.role === 'assistant' && message.status === 'streaming' && !message.text && (
            // Render p.
            <p className="chat-first-token" role="status">
              {/* Render span. */}
              <span className="chat-pulse" aria-hidden="true" />
              Connecting to Gemini and waiting for the first token…
            </p>
          )}
          {/* Render the matching state/condition only. */}
          {message.text && (message.role === 'assistant' ? (
            // Render div.
            <div className="chat-markdown">
              {/* Render ReactMarkdown with the supplied props. */}
              <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml
                components={{
                  // Do not load externally supplied images from model output.
                  img: ({ alt }) => <span>{alt}</span>,
                  // Set the a option/value.
                  a: ({ href, children }) => (
                    // Render a.
                    <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>
                  ),
                }}>
                {message.text}
              </ReactMarkdown>
            </div>
          ) : <p className="chat-message-text">{message.text}</p>)}
          {/* Render one entry for each item. */}
          {message.playlist && (
            // Render div.
            <div className="chat-playlist-preview">
              {/* Render h3. */}
              <h3>{message.playlist.preview.proposal.name}</h3>
              {/* Render p. */}
              <p>{message.playlist.preview.proposal.description}</p>
              {/* Render p. */}
              <p>{message.playlist.preview.proposal.public ? 'Public' : 'Private'} · {message.playlist.preview.matched_count} unique tracks matched</p>
              {/* Render the matching state/condition only. */}
              {message.playlist.preview.total_duration_ms > 0 && <p>
                Listening time: {Math.floor(message.playlist.preview.total_duration_ms / 60000)} min {Math.round(message.playlist.preview.total_duration_ms % 60000 / 1000)} sec
              </p>}
              {/* Render the matching state/condition only. */}
              {message.playlist.preview.constraint_warning && <p className="chat-error" role="alert">{message.playlist.preview.constraint_warning}</p>}
              {/* Render ul. */}
              <ul>{message.playlist.preview.matches.map((match, index) => (
                // Render li.
                <li key={index}>
                  {/* Render strong. */}
                  <strong>{match.track?.title ?? match.recommendation.title}</strong>
                  {' — '}{match.track?.artists.join(', ') ?? match.recommendation.artist}
                  {/* Render the matching state/condition only. */}
                  {match.track && message.playlist?.preview.proposal.provider === 'youtube' && ' (uploader)'}
                  {/* Render span. */}
                  <span className="chat-message-note"> · {match.status.replaceAll('_', ' ')}</span>
                </li>
              ))}</ul>
              {/* Render p. */}
              <p className="chat-message-note">{message.playlist.preview.proposal.provider === 'youtube'
                ? 'The first best match is selected when videos tie. Review titles and uploaders carefully; YouTube metadata does not verify recording identity. Unmatched and duplicate videos are skipped.'
                : 'The first best match is selected. Unmatched and duplicate suggestions are skipped.'}</p>
              {/* Render the matching state/condition only. */}
              {message.playlist.error && <p className="chat-error" role="alert">{message.playlist.error}</p>}
              {/* Render the matching state/condition only. */}
              {message.playlist.result ? (
                // Render p.
                <p role="status">
                  {/* Render the matching state/condition only. */}
                  {message.playlist.result.status === 'complete'
                    ? `Playlist created with ${message.playlist.result.added} ${message.playlist.result.added === 1 ? 'track' : 'tracks'}. `
                    : `Creation needs review (${message.playlist.result.added}/${message.playlist.result.total} confirmed). Check ${message.playlist.preview.proposal.provider === 'youtube' ? 'YouTube' : 'Spotify'} before making another playlist. `}
                  {/* Render the matching state/condition only. */}
                  {message.playlist.result.url && <a href={message.playlist.result.url} target="_blank" rel="noopener noreferrer">Open in {message.playlist.preview.proposal.provider === 'youtube' ? 'YouTube' : 'Spotify'}</a>}
                </p>
              ) : (
                // Render button and handle onClick.
                <button type="button" disabled={message.playlist.creating || !message.playlist.preview.matched_count || !!message.playlist.preview.constraint_warning}
                  onClick={() => void onCreatePlaylist(message.id)}>
                  {/* Render the matching state/condition only. */}
                  {message.playlist.creating ? 'Creating playlist…' : `Approve and create on ${message.playlist.preview.proposal.provider === 'youtube' ? 'YouTube' : 'Spotify'}`}
                </button>
              )}
            </div>
          )}
          {/* Render the matching state/condition only. */}
          {message.status === 'stopped' && <p className="chat-message-note">Response stopped.</p>}
          {/* Render the matching state/condition only. */}
          {message.status === 'error' && <p className="chat-message-note">Response unavailable.</p>}
        </article>
      ))}
    </div>
  )
}

// Export this module's public entry point.
export default MessageList

/* File summary
 * - Renders safe Markdown, progress, and playlist previews.
 * - Shows warnings, match status, approval controls, and creation results.
 * - Follows new messages only while the reader stays near the bottom.
 */
