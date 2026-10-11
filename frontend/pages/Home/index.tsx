import Navbar from '../../Components/Navbar'
import Sidebar from '../../Components/Sidebar'
import { useSpotifyAuth } from '../../src/lib/auth'
import './index.css'

const Home = () => {
  const { data: authData } = useSpotifyAuth()
  const spotifyUser = authData?.profile

  return (
    <div className="home-layout">
      <Navbar />
      <div className="home-body">
        <Sidebar />
        <main className="content-container">
          {spotifyUser && (
            <div className="header">
              <p className="welcome-text">Welcome {String(spotifyUser.display_name ?? 'Spotify User')}</p>
              
            </div>
          )}
        </main>
      </div>
    </div>
  )
}

export default Home