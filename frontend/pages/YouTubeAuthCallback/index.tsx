import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { isAxiosError } from 'axios'
import { useYouTubeAuthActions } from '../../src/lib/youtubeAuth'
import { getYouTubeUser } from '../../src/lib/youtubeApi'

const YouTubeAuthCallback = () => {
  const navigate = useNavigate()
  const { setAuth, clearAuth } = useYouTubeAuthActions()
  // Capture once before removing credentials; StrictMode replays the effect.
  const params = useRef(new URLSearchParams(window.location.hash.slice(1)))

  useEffect(() => {
    let cancelled = false
    const values = params.current
    window.history.replaceState(null, '', window.location.pathname)
    const accessToken = values.get('access_token')
    if (values.has('error') || !accessToken || !values.get('token_type')) {
      clearAuth()
      navigate('/login?error=youtube', {
        replace: true,
        state: { youtubeError: values.get('error_description') ?? 'The YouTube callback did not include valid credentials. Start login again.' },
      })
      return
    }
    // A missing refresh token is valid on subsequent Google authorizations.
    setAuth({
      access_token: accessToken,
      // Do not carry a refresh token across a possible Google account switch.
      refresh_token: values.get('refresh_token'),
      token_type: values.get('token_type'), expires_in: values.get('expires_in'),
      scope: values.get('scope'), profile: null,
    })
    void getYouTubeUser().then((profile) => {
      if (cancelled) return
      setAuth({ profile })
      navigate('/', { replace: true })
    }).catch((error: unknown) => {
      if (cancelled) return
      clearAuth()
      let message = 'Google authorization completed, but the profile request failed.'
      if (isAxiosError(error)) {
        const status = error.response?.status
        if (!error.response) message += ' The backend could not be reached. Check the API server and CORS origin.'
        else if (status === 401 || status === 403) message += ' Google rejected profile access. Reconnect and grant profile permissions.'
        else if (status === 502 || status === 504) message += ' The backend could not reach Google successfully. Check its network, TLS certificates, or timeout.'
        else message += ` The backend returned HTTP ${status}.`
      }
      navigate('/login?error=youtube', { replace: true, state: { youtubeError: message } })
    })
    return () => { cancelled = true }
  }, [navigate, setAuth, clearAuth])

  return <p role="status">Connecting your YouTube account…</p>
}

export default YouTubeAuthCallback