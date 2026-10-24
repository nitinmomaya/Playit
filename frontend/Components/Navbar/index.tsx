// Import auth dependencies.
import { useSpotifyAuthActions } from '../../src/lib/auth'
// Import youtubeAuth dependencies.
import { useYouTubeAuthActions } from '../../src/lib/youtubeAuth'
// Import index.css dependencies.
import './index.css'
// Import Button dependencies.
import Button from '../Button'

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
        {/* Render div. */}
        <div>Playit</div>
      {/* Render Button and handle onClickFunction. */}
      <Button name="Logout" onClickFunction={logout} />
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
