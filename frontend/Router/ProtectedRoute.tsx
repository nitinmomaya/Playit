import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useSpotifyAuth } from '../src/lib/auth'
import { useYouTubeAuth } from '../src/lib/youtubeAuth'

const ProtectedRoute = () => {
  const location = useLocation()
  const { data: spotify } = useSpotifyAuth()
  const { data: youtube } = useYouTubeAuth()
  const isAuthenticated = !!spotify?.access_token || !!youtube?.access_token

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return <Outlet />
}

export default ProtectedRoute
