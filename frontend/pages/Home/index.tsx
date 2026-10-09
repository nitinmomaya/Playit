import React from 'react'
import { useQuery } from '@tanstack/react-query'

import Navbar from '../../Components/Navbar'
import { useSpotifyAuth } from '../../src/lib/auth'
import { getSpotifyUser } from '../../src/lib/spotifyApi'

const Home = () => {
  const { data: authData } = useSpotifyAuth()

  const {
    data: spotifyUser,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['spotifyUser', authData?.access_token, authData?.refresh_token],
    queryFn: getSpotifyUser,
    enabled: !!authData?.access_token,
  })

  return (
    <>
      <h1>Home</h1>
      {isLoading && <p>Loading Spotify profile...</p>}
      {isError && <p>Failed to load profile: {String(error)}</p>}
      {!isLoading && !isError && spotifyUser && (
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