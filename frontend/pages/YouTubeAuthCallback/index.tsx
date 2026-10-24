// Use React state/lifecycle APIs.
import { useEffect, useRef } from 'react'
// Use client-side routing and navigation.
import { useNavigate } from 'react-router-dom'
// Make JSON requests through Axios.
import { isAxiosError } from 'axios'
// Import youtubeAuth dependencies.
import { useYouTubeAuthActions } from '../../src/lib/youtubeAuth'
// Import youtubeApi dependencies.
import { getYouTubeUser } from '../../src/lib/youtubeApi'

// Keep YouTubeAuthCallback across renders without triggering updates.
const YouTubeAuthCallback = () => {
  // Prepare navigate for the following operation.
  const navigate = useNavigate()
  // Prepare { setAuth, clearAuth } for the following operation.
  const { setAuth, clearAuth } = useYouTubeAuthActions()
  // Capture once before removing credentials; StrictMode replays the effect.
  const params = useRef(new URLSearchParams(window.location.hash.slice(1)))

  // Remove credential/error fragments from the address bar.
  useEffect(() => {
    // Prepare cancelled for the following operation.
    let cancelled = false
    // Prepare values for the following operation.
    const values = params.current
    // Remove credential/error fragments from the address bar.
    window.history.replaceState(null, '', window.location.pathname)
    // Prepare accessToken for the following operation.
    const accessToken = values.get('access_token')
    // Check values.has('error') || !accessToken || !values.get('token_type').
    if (values.has('error') || !accessToken || !values.get('token_type')) {
      // Call clearAuth.
      clearAuth()
      // Navigate after the auth or request result is known.
      navigate('/login?error=youtube', {
        // Set the replace option/value.
        replace: true,
        // Set the state option/value.
        state: { youtubeError: values.get('error_description') ?? 'The YouTube callback did not include valid credentials. Start login again.' },
      })
      // Return the current operation's result.
      return
    }
    // A missing refresh token is valid on subsequent Google authorizations.
    setAuth({
      // Set the access_token option/value.
      access_token: accessToken,
      // Do not carry a refresh token across a possible Google account switch.
      refresh_token: values.get('refresh_token'),
      // Set the token_type option/value.
      token_type: values.get('token_type'), expires_in: values.get('expires_in'),
      // Set the scope option/value.
      scope: values.get('scope'), profile: null,
    })
    // Navigate after the auth or request result is known.
    void getYouTubeUser().then((profile) => {
      // Check cancelled.
      if (cancelled) return
      // Call setAuth.
      setAuth({ profile })
      // Navigate after the auth or request result is known.
      navigate('/', { replace: true })
    }).catch((error: unknown) => {
      // Check cancelled.
      if (cancelled) return
      // Call clearAuth.
      clearAuth()
      // Prepare message for the following operation.
      let message = 'Google authorization completed, but the profile request failed.'
      // Check isAxiosError(error).
      if (isAxiosError(error)) {
        // Prepare status for the following operation.
        const status = error.response?.status
        // Check !error.response.
        if (!error.response) message += ' The backend could not be reached. Check the API server and CORS origin.'
        else if (status === 401 || status === 403) message += ' Google rejected profile access. Reconnect and grant profile permissions.'
        else if (status === 502 || status === 504) message += ' The backend could not reach Google successfully. Check its network, TLS certificates, or timeout.'
        else message += ` The backend returned HTTP ${status}.`
      }
      // Navigate after the auth or request result is known.
      navigate('/login?error=youtube', { replace: true, state: { youtubeError: message } })
    })
    // Return the current operation's result.
    return () => { cancelled = true }
  }, [navigate, setAuth, clearAuth])

  // Render the component UI.
  return <p role="status">Connecting your YouTube account…</p>
}

// Export this module's public entry point.
export default YouTubeAuthCallback

/* File summary
 * - Reads and removes the Google callback fragment safely across effect replays.
 * - Stores Google tokens separately and loads the account profile.
 * - Returns callback/profile errors to the login page.
 */
