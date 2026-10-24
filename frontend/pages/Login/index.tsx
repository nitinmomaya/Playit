// Import Button dependencies.
import Button from '../../Components/Button'
// Import spotifyApi dependencies.
import { spotifyApi } from '../../src/lib/spotifyApi'
// Import youtubeApi dependencies.
import { youtubeApi } from '../../src/lib/youtubeApi'
// Use client-side routing and navigation.
import { useLocation, useSearchParams } from 'react-router-dom'
// Import index.css dependencies.
import './index.css'
// Define the Login handler/helper.
const Login = () => {
  // Prepare [params] for the following operation.
  const [params] = useSearchParams()
    // Prepare location for the following operation.
    const location = useLocation()
    // Prepare youtubeError for the following operation.
    const youtubeError = typeof location.state?.youtubeError === 'string'
      ? location.state.youtubeError
      : 'Could not connect YouTube. Please start login again.'

    // Define the handleSpotifyLogin handler/helper.
    const handleSpotifyLogin=()=>{
        // Navigate the browser to the selected destination.
        window.location.href = `${spotifyApi.defaults.baseURL}/login`
    }
  // Return the current operation's result.
  return (
   <>
   {/* Render div. */}
   <div className="container">
    {/* Render div. */}
    <div className="box">
   {/* Render div. */}
   <div className="head-content">
     {/* Render h1. */}
     <h1>Welcome Back!</h1>
    {/* Render p. */}
    <p>Choose your music account to continue.</p>
   </div>
    
    {/* Render the matching state/condition only. */}
    {params.get('error') === 'youtube' && <p role="alert">{youtubeError}</p>}
    {/* Render div. */}
    <div className="login-providers">
      {/* Render Button and handle onClickFunction. */}
      <Button onClickFunction={handleSpotifyLogin} name="Login with Spotify"/>
      {/* Render Button and handle onClickFunction. */}
      <Button onClickFunction={() => { window.location.href = `${youtubeApi.defaults.baseURL}/login` }} name="Login with YouTube" isSecondaryButton />
    </div>
    {/* Render p. */}
    <p className="login-note">Chat with Playit using either account. Review song matches and approve before creating a playlist on Spotify or YouTube.</p>
   </div>
   </div>
   </>
  )
}

// Export this module's public entry point.
export default Login

/* File summary
 * - Starts Spotify or YouTube login through the backend.
 * - Displays sanitized YouTube callback errors.
 */
