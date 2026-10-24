// StrictMode repeats selected development lifecycle work to expose unsafe effects.
import { StrictMode } from 'react'
// createRoot connects the React component tree to the HTML root element.
import { createRoot } from 'react-dom/client'
// App owns global providers and the application's router.
import App from './App.tsx'
// A top-level boundary renders fallback UI when a descendant fails to render.
import ErrorBoundary from '../Components/ErrorBoundary'

// index.html supplies #root; the non-null assertion documents that contract.
createRoot(document.getElementById('root')!).render(
  // The JSX tree below is passed as the argument to React's render method.
  <StrictMode>
    {/* fullPage selects the error boundary's full-screen fallback layout. */}
    <ErrorBoundary fullPage>
      {/* Mount the actual application inside the error boundary. */}
      <App />
      {/* End the subtree protected by the full-page error boundary. */}
    </ErrorBoundary>
    {/* End StrictMode's development-only checking scope. */}
  </StrictMode>,
  // Complete the initial React root render call.
)

/* File summary
 * - Mounts React in the HTML root.
 * - Enables StrictMode and a full-page render-error boundary.
 */
