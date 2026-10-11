import { useSpotifyAuthActions } from '../../src/lib/auth'
import { getSpotifyUser } from '../../src/lib/spotifyApi'
import './index.css'
import Button from '../Button'

const Navbar = () => {
  const { clearAuth } = useSpotifyAuthActions()

  const logout = () => {
      clearAuth()
      window.location.href = '/login'
  }

  const getUserDetails=async()=>{

    const res= await getSpotifyUser();
    console.log("user details", res)
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