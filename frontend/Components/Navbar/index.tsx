import { useSpotifyAuthActions } from '../../src/lib/auth'
import { useYouTubeAuthActions } from '../../src/lib/youtubeAuth'
import './index.css'
import Button from '../Button'

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
        <div>Playit</div>
      <Button name="Logout" onClickFunction={logout} />
     </div>
    </>
  )
}

export default Navbar