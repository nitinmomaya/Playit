import Button from '../../Components/Button'
import { spotifyApi } from '../../src/lib/spotifyApi'
import { youtubeApi } from '../../src/lib/youtubeApi'
import { useLocation, useSearchParams } from 'react-router-dom'
import './index.css'
const Login = () => {
  const [params] = useSearchParams()
    const location = useLocation()
    const youtubeError = typeof location.state?.youtubeError === 'string'
      ? location.state.youtubeError
      : 'Could not connect YouTube. Please start login again.'

    const handleSpotifyLogin=()=>{
        window.location.href = `${spotifyApi.defaults.baseURL}/login`
    }
  return (
   <>
   <div className="container">
    <div className="box">
   <div className="head-content">
     <h1>Welcome Back!</h1>
    <p>Choose your music account to continue.</p>
   </div>
    
    {params.get('error') === 'youtube' && <p role="alert">{youtubeError}</p>}
    <div className="login-providers">
      <Button onClickFunction={handleSpotifyLogin} name="Login with Spotify"/>
      <Button onClickFunction={() => { window.location.href = `${youtubeApi.defaults.baseURL}/login` }} name="Login with YouTube" isSecondaryButton />
    </div>
    <p className="login-note">Chat with Playit using either account. Review song matches and approve before creating a playlist on Spotify or YouTube.</p>
   </div>
   </div>
   </>
  )
}

export default Login