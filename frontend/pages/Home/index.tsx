import Navbar from '../../Components/Navbar'
import Sidebar from '../../Components/Sidebar'
import ErrorBoundary from '../../Components/ErrorBoundary'
import Chat from '../../Components/Chat'
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
            <Chat displayName={String(spotifyUser?.display_name ?? 'music lover')} />
          </ErrorBoundary>
        </main>
      </div>
    </div>
  )
}

export default Home