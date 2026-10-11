import { Component, type ErrorInfo, type ReactNode } from 'react'
import './index.css'

type Props = {
  children: ReactNode
  fullPage?: boolean
}

type State = {
  hasError: boolean
}

class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    if (import.meta.env.DEV) {
      console.error('Playit rendering error:', error, info.componentStack)
    }
  }

  render() {
    if (!this.state.hasError) return this.props.children

    return (
      <section
        className={`error-boundary${this.props.fullPage ? ' error-boundary--full-page' : ''}`}
        role="alert"
        aria-labelledby="error-boundary-title"
      >
        <div className="error-boundary__card">
          <span className="error-boundary__icon" aria-hidden="true">!</span>
          <p className="error-boundary__eyebrow">LET’S GET BACK ON TRACK</p>
          <h1 id="error-boundary-title">Something went wrong</h1>
          <p className="error-boundary__description">
            This part of Playit couldn’t load. Try again, or reload the page for a fresh start.
          </p>
          <div className="error-boundary__actions">
            <button
              type="button"
              className="error-boundary__retry"
              onClick={() => this.setState({ hasError: false })}
            >
              Try again
            </button>
            <button type="button" onClick={() => window.location.reload()}>
              Reload page
            </button>
          </div>
          <p className="error-boundary__note">Reloading may require signing in again.</p>
          <a className="error-boundary__link" href="/login">Back to login</a>
        </div>
      </section>
    )
  }
}

export default ErrorBoundary