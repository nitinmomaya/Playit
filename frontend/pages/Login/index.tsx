import { spotifyApi } from '../../src/lib/spotifyApi'

const Login = () => {

    const handleSpotifyLogin=()=>{
        window.location.href = `${spotifyApi.defaults.baseURL}/login`
    }
  return (
   <>
   <h1>Login</h1>
   <button onClick={handleSpotifyLogin}>Login with Spotify</button>
   </>
  )
}

export default Login