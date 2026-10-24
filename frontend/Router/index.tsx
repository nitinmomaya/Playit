// Use client-side routing and navigation.
import { BrowserRouter, Route, Routes } from 'react-router-dom'
// Import AuthCallback dependencies.
import AuthCallback from '../pages/AuthCallback'
// Import YouTubeAuthCallback dependencies.
import YouTubeAuthCallback from '../pages/YouTubeAuthCallback'
// Import Home dependencies.
import Home from '../pages/Home'
// Import Login dependencies.
import Login from '../pages/Login'
// Import ProtectedRoute dependencies.
import ProtectedRoute from './ProtectedRoute'

// Define the Router handler/helper.
const Router = () => {
  // Return the current operation's result.
  return (
    // Render BrowserRouter with the supplied props.
    <BrowserRouter>
      {/* Render Routes with the supplied props. */}
      <Routes>
        {/* Render Route with the supplied props. */}
        <Route path="/login" element={<Login />} />
        {/* Render Route with the supplied props. */}
        <Route path="/auth/callback" element={<AuthCallback />} />
        {/* Render Route with the supplied props. */}
        <Route path="/auth/youtube/callback" element={<YouTubeAuthCallback />} />
        {/* Render Route with the supplied props. */}
        <Route element={<ProtectedRoute />}>
          {/* Render Route with the supplied props. */}
          <Route path="/" element={<Home />} />
          {/* Render Route with the supplied props. */}
          <Route path="*" element={<p>Page not found</p>} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

// Export this module's public entry point.
export default Router

/* File summary
 * - Defines public login and OAuth callback routes.
 * - Protects Home behind provider-token presence.
 */
