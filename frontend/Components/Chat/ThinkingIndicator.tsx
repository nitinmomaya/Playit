import type { ChatMessage } from './types'

// Block 3: public progress only. Never expose private model chain-of-thought.
const ThinkingIndicator = ({ message }: { message: ChatMessage }) => (
  <details className="chat-progress">
    <summary>
      {message.status === 'streaming' && <span className="chat-pulse" aria-hidden="true" />}
      {message.status === 'streaming' ? 'Thinking / responding…' : 'Response activity'}
    </summary>
    <p>Progress updates, not the model’s private reasoning.</p>
    <ul>{message.progress.map((step, index) => <li key={index}>{step}</li>)}</ul>
  </details>
)

export default ThinkingIndicator