// Import Navbar dependencies.
import Navbar from '../../Components/Navbar'
// Import ErrorBoundary dependencies.
import ErrorBoundary from '../../Components/ErrorBoundary'
// Import Chat dependencies.
import Chat from '../../Components/Chat'
// Import auth dependencies.
import { useSpotifyAuth } from '../../src/lib/auth'
// Import youtubeAuth dependencies.
import { useYouTubeAuth } from '../../src/lib/youtubeAuth'
// Import index.css dependencies.
import './index.css'

// Define the Home handler/helper.
const Home = () => {
  // Prepare { data: authData } for the following operation.
  const { data: authData } = useSpotifyAuth()
  // Prepare { data: youtubeAuth } for the following operation.
  const { data: youtubeAuth } = useYouTubeAuth()
  // Prepare spotifyUser for the following operation.
  const spotifyUser = authData?.profile
  const provider = authData?.access_token ? 'Spotify' : 'YouTube'

  // Return the current operation's result.
  return (
    <div className={provider.toLowerCase() === 'youtube' ? 'home-layout home-layout--youtube' : 'home-layout'}>
      <Navbar />
      {/* Render div. */}
      <div className="home-body">
        <main className="content-container">
          {/* Protect this subtree from render failures. */}
          <ErrorBoundary>
            {/* Render Chat with the supplied props. */}
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

// Export this module's public entry point.
export default Home

/* File summary
 * - Combines navigation and chat.
 * - Chooses the active provider and display name from auth state.
 */
