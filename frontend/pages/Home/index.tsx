import React from 'react'

import Navbar from '../../Components/Navbar'
import { useSpotifyAuth } from '../../src/lib/auth'

const Home = () => {
  const { data: authData } = useSpotifyAuth()
  const spotifyUser = authData?.profile

  return (
    <>
      <h1>Home</h1>
      {spotifyUser && (
        <>
          <p>Welcome {String(spotifyUser.display_name ?? 'Spotify User')}</p>
          <p>Email: {String(spotifyUser.email ?? 'Not available')}</p>
          <p>Country: {String(spotifyUser.country ?? 'Not available')}</p>
        </>
      )}
      <Navbar />
    </>
  )
}

export default Home