// Import App.css dependencies.
import './App.css'
// Use the shared request/state cache.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
// Import Router dependencies.
import Router from '../Router'

// Prepare queryClient for the following operation.
const queryClient = new QueryClient()

// Define App.
function App() {
  // Return the current operation's result.
  return (
    // Render QueryClientProvider with the supplied props.
    <QueryClientProvider client={queryClient}>
      {/* Render Router with the supplied props. */}
      <Router />
    </QueryClientProvider>
  )
}

// Export this module's public entry point.
export default App

/* File summary
 * - Creates the shared TanStack Query cache.
 * - Wraps client routes in QueryClientProvider.
 */
