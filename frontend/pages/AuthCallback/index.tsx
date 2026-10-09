import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

const AuthCallback = () => {
  const navigate = useNavigate()

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    console.log("win", window.location.search, "params", params);
    const profile = params.get('profile')
    const accessToken = params.get('access_token')
    const refreshToken = params.get('refresh_token')
    const tokenType = params.get('token_type')
    const expiresIn = params.get('expires_in')
    const scope = params.get('scope')

    if (accessToken) {
      localStorage.setItem('spotify_access_token', accessToken)
    }

    if (refreshToken) {
      localStorage.setItem('spotify_refresh_token', refreshToken)
    }

    if (tokenType) {
      localStorage.setItem('spotify_token_type', tokenType)
    }

    if (expiresIn) {
      localStorage.setItem('spotify_expires_in', expiresIn)
    }

    if (scope) {
      localStorage.setItem('spotify_scope', scope)
    }

    if (profile) {
      try {
        const parsedProfile = JSON.parse(profile)
        localStorage.setItem('spotify_user', JSON.stringify(parsedProfile))
      } catch {
        localStorage.setItem('spotify_user', profile)
      }
    }

    navigate('/', { replace: true })
  }, [navigate])

  return <p>Signing you in...</p>
}

export default AuthCallback
