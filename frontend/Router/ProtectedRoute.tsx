import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useSpotifyAuth } from '../src/lib/auth'

const ProtectedRoute = () => {
  const location = useLocation()
  const { data } = useSpotifyAuth()
  console.log('ProtectedRoute data:', data) // Debugging line
  const isAuthenticated = !!data?.access_token

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return <Outlet />
}

export default ProtectedRoute
