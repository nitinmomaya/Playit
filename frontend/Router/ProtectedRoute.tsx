// Use client-side routing and navigation.
import { Navigate, Outlet, useLocation } from 'react-router-dom'

// Import auth dependencies.
import { useSpotifyAuth } from '../src/lib/auth'
// Import youtubeAuth dependencies.
import { useYouTubeAuth } from '../src/lib/youtubeAuth'

// Define the ProtectedRoute handler/helper.
const ProtectedRoute = () => {
  // Prepare location for the following operation.
  const location = useLocation()
  // Prepare { data: spotify } for the following operation.
  const { data: spotify } = useSpotifyAuth()
  // Prepare { data: youtube } for the following operation.
  const { data: youtube } = useYouTubeAuth()
  // Prepare isAuthenticated for the following operation.
  const isAuthenticated = !!spotify?.access_token || !!youtube?.access_token

  // Check !isAuthenticated.
  if (!isAuthenticated) {
    // Return the current operation's result.
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  // Return the current operation's result.
  return <Outlet />
}

// Export this module's public entry point.
export default ProtectedRoute

/* File summary
 * - Allows access when either provider has an in-memory token.
 * - Redirects unauthenticated navigation to login.
 */
