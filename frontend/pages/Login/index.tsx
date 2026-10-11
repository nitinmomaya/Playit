import Button from '../../Components/Button'
import { spotifyApi } from '../../src/lib/spotifyApi'
import './index.css'
const Login = () => {

    const handleSpotifyLogin=()=>{
        window.location.href = `${spotifyApi.defaults.baseURL}/login`
    }
  return (
   <>
   <div className="container">
    <div className="box">
   <div className="head-content">
     <h1>Welcome Back!</h1>
    <p>Please login with your Spotify account to continue.</p>
   </div>
    
    <Button onClickFunction={handleSpotifyLogin} name="Login with Spotify"/>
   </div>
   </div>
   </>
  )
}

export default Login