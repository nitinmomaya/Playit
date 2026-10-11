import Navbar from '../../Components/Navbar'
import { useSpotifyAuth } from '../../src/lib/auth'
import './index.css'

const Home = () => {
  const { data: authData } = useSpotifyAuth()
  const spotifyUser = authData?.profile

  return (
    <>
      <Navbar />
      {spotifyUser && (
        <>
         <div className="container">
          <div className="header">
            <p className="welcome-text">Welcome {String(spotifyUser.display_name ?? 'Spotify User')}</p>
          </div>
         </div>
        </>
      )}
    </>
  )
}

export default Home