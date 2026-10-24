import Navbar from '../../Components/Navbar'
import ErrorBoundary from '../../Components/ErrorBoundary'
import Chat from '../../Components/Chat'
import { useSpotifyAuth } from '../../src/lib/auth'
import { useYouTubeAuth } from '../../src/lib/youtubeAuth'
import './index.css'

const Home = () => {
  const { data: authData } = useSpotifyAuth()
  const { data: youtubeAuth } = useYouTubeAuth()
  const spotifyUser = authData?.profile
  const provider = authData?.access_token ? 'Spotify' : 'YouTube'

  return (
    <div className={provider.toLowerCase() === 'youtube' ? 'home-layout home-layout--youtube' : 'home-layout'}>
      <Navbar />
      <div className="home-body">
        <main className="content-container">
          <ErrorBoundary>
            <Chat provider={provider} displayName={String(
              provider.toLocaleLowerCase() === 'spotify' ? spotifyUser?.display_name ?? 'music lover'
                : youtubeAuth?.profile?.name ?? 'music lover',
            )} />
          </ErrorBoundary>
        </main>
      </div>
    </div>
  )
}

export default Home