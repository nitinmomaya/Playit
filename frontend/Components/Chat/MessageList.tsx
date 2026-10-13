import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import ThinkingIndicator from './ThinkingIndicator'
import type { ChatMessage } from './types'

// Block 4: render assistant Markdown safely; raw HTML is not enabled.
const MessageList = ({ messages }: { messages: ChatMessage[] }) => {
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
              Gemini is preparing your response…
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
          {message.status === 'stopped' && <p className="chat-message-note">Response stopped.</p>}
          {message.status === 'error' && <p className="chat-message-note">Response unavailable.</p>}
        </article>
      ))}
    </div>
  )
}

export default MessageList