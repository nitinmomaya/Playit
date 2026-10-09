import React from 'react'

import { useSpotifyAuthActions } from '../../src/lib/auth'

const Navbar = () => {
  const { clearAuth } = useSpotifyAuthActions()

  const logout = () => {
    clearAuth()
    window.location.href = '/login'
  }

  return (
    <>
      <div>Navbar</div>
      <button onClick={logout}>Logout</button>
    </>
  )
}

export default Navbar