import Navbar from '../../Components/Navbar'
import Sidebar from '../../Components/Sidebar'
import ErrorBoundary from '../../Components/ErrorBoundary'
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
          <ErrorBoundary>
          {spotifyUser && (
            <div className="header">
              <p className="welcome-text">Welcome {String(spotifyUser.display_name ?? 'Spotify User')}</p>
              
            </div>
          )}
          </ErrorBoundary>
        </main>
      </div>
    </div>
  )
}

export default Home