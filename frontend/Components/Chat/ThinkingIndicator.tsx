// Import types dependencies.
import type { ChatMessage } from './types'

// Block 3: public progress only. Never expose private model chain-of-thought.
const ThinkingIndicator = ({ message }: { message: ChatMessage }) => (
  // Render details.
  <details className="chat-progress">
    {/* Render summary. */}
    <summary>
      {/* Render the matching state/condition only. */}
      {message.status === 'streaming' && <span className="chat-pulse" aria-hidden="true" />}
      {/* Render the matching state/condition only. */}
      {message.status === 'streaming' ? 'Thinking / responding…' : 'Response activity'}
    </summary>
    {/* Render p. */}
    <p>Progress updates, not the model’s private reasoning.</p>
    {/* Render ul. */}
    <ul>{message.progress.map((step, index) => <li key={index}>{step}</li>)}</ul>
  </details>
)

// Export this module's public entry point.
export default ThinkingIndicator

/* File summary
 * - Shows public progress events in an expandable section.
 * - Does not expose the model's private reasoning.
 */
