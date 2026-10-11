import { useSpotifyAuthActions } from '../../src/lib/auth'
import { getSpotifyUser, spotifyApi } from '../../src/lib/spotifyApi'

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
      <div>Navbar</div>
      <div>Get User Details</div>
      <button onClick={getUserDetails}> Get User Details</button>
      <button onClick={logout}>Logout</button>
    </>
  )
}

export default Navbar