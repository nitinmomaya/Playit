// Use React state/lifecycle APIs.
import { Component, type ErrorInfo, type ReactNode } from 'react'
// Import index.css dependencies.
import './index.css'

// Describe the Props data contract.
type Props = {
  // Define children in this data shape.
  children: ReactNode
  // Define fullPage in this data shape.
  fullPage?: boolean
}

// Describe the State data contract.
type State = {
  // Define hasError in this data shape.
  hasError: boolean
}

// Group ErrorBoundary behavior and state.
class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  // Implement getDerivedStateFromError for this component.
  static getDerivedStateFromError(): State {
    // Return the current operation's result.
    return { hasError: true }
  }

  // Implement componentDidCatch for this component.
  componentDidCatch(error: Error, info: ErrorInfo) {
    // Check import.meta.env.DEV.
    if (import.meta.env.DEV) {
      // Call console.error.
      console.error('Playit rendering error:', error, info.componentStack)
    }
  }

  // Implement render for this component.
  render() {
    // Check !this.state.hasError.
    if (!this.state.hasError) return this.props.children

    // Return the current operation's result.
    return (
      // Render section.
      <section
        className={`error-boundary${this.props.fullPage ? ' error-boundary--full-page' : ''}`}
        role="alert"
        aria-labelledby="error-boundary-title"
      >
        {/* Render div. */}
        <div className="error-boundary__card">
          {/* Render span. */}
          <span className="error-boundary__icon" aria-hidden="true">!</span>
          {/* Render p. */}
          <p className="error-boundary__eyebrow">LET’S GET BACK ON TRACK</p>
          {/* Render h1. */}
          <h1 id="error-boundary-title">Something went wrong</h1>
          {/* Render p. */}
          <p className="error-boundary__description">
            This part of Playit couldn’t load. Try again, or reload the page for a fresh start.
          </p>
          {/* Render div. */}
          <div className="error-boundary__actions">
            {/* Render button and handle onClick. */}
            <button
              type="button"
              className="error-boundary__retry"
              onClick={() => this.setState({ hasError: false })}
            >
              Try again
            </button>
            {/* Render button and handle onClick. */}
            <button type="button" onClick={() => window.location.reload()}>
              Reload page
            </button>
          </div>
          {/* Render p. */}
          <p className="error-boundary__note">Reloading may require signing in again.</p>
          {/* Render a. */}
          <a className="error-boundary__link" href="/login">Back to login</a>
        </div>
      </section>
    )
  }
}

// Export this module's public entry point.
export default ErrorBoundary

/* File summary
 * - Catches descendant render failures and shows recovery actions.
 * - Logs render details only in development.
 * - Does not replace async API error handling.
 */
