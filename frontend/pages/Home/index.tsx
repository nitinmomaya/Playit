import React from 'react'

import Navbar from '../../Components/Navbar'
import { useSpotifyAuth } from '../../src/lib/auth'

const Home = () => {
  const { data } = useSpotifyAuth()
  const profile = data?.profile as Record<string, unknown> | null

  return (
    <>
      <h1>Home</h1>
      <p>Welcome {String(profile?.display_name ?? 'Spotify User')}</p>
      <p>Email: {String(profile?.email ?? 'Not available')}</p>
      <Navbar />
    </>
  )
}

export default Home