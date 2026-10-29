// Import auth dependencies.
import { useSpotifyAuthActions } from '../../src/lib/auth'
// Import youtubeAuth dependencies.
import { useYouTubeAuthActions } from '../../src/lib/youtubeAuth'
// Import index.css dependencies.
import './index.css'
// Define the Navbar handler/helper.
const Navbar = () => {
  // Prepare { clearAuth } for the following operation.
  const { clearAuth } = useSpotifyAuthActions()
  // Prepare { clearAuth: clearYouTubeAuth } for the following operation.
  const { clearAuth: clearYouTubeAuth } = useYouTubeAuthActions()

  // Define the logout handler/helper.
  const logout = () => {
      // Call clearAuth.
      clearAuth()
      // Call clearYouTubeAuth.
      clearYouTubeAuth()
      // Navigate the browser to the selected destination.
      window.location.href = '/login'
  }

  // Return the current operation's result.
  return (
    <>
     {/* Render div. */}
     <div className="navbar">
        <div className="navbar-brand">Playit</div>
  {/* Render the logout action and clear both provider sessions. */}
  <button className="navbar-logout" type="button" onClick={logout}>Logout</button>
     </div>
    </>
  )
}

// Export this module's public entry point.
export default Navbar

/* File summary
 * - Shows the application header and logout control.
 * - Clears both in-memory provider logins on logout.
 */
