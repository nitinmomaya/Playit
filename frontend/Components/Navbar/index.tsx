import { useSpotifyAuthActions } from '../../src/lib/auth'
import { useYouTubeAuthActions } from '../../src/lib/youtubeAuth'
import './index.css'

const Navbar = () => {
  const { clearAuth } = useSpotifyAuthActions()
  const { clearAuth: clearYouTubeAuth } = useYouTubeAuthActions()

  const logout = () => {
      clearAuth()
      clearYouTubeAuth()
      window.location.href = '/login'
  }

  return (
    <>
     <div className="navbar">
        <div className="navbar-brand">Playit</div>
      <button className="navbar-logout" type="button" onClick={logout}>Logout</button>
     </div>
    </>
  )
}

export default Navbar