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
      <Button
        onClickFunction={handleSpotifyLogin}
        name="Login with Spotify"
        icon={<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="11" fill="white" />
          <path d="M6.2 9.2c3.7-1.1 8.1-.7 11.4 1.3M7 12.3c3-0.9 6.8-.6 9.5 1.1m-8.7 1.8c2.4-.7 5.3-.4 7.5.9" stroke="#1DB954" strokeWidth="1.7" strokeLinecap="round" />
        </svg>}
      />
      <Button
        onClickFunction={() => { window.location.href = `${youtubeApi.defaults.baseURL}/login` }}
        name="Login with YouTube"
        isSecondaryButton
        icon={<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <rect x="1" y="4" width="22" height="16" rx="5" fill="white" />
          <path d="M10 8.5 16 12l-6 3.5v-7Z" fill="#FF0033" />
        </svg>}
      />
    </div>
    <p className="login-note">Chat with Playit using either account. Review song matches and approve before creating a playlist on Spotify or YouTube.</p>
   </div>
   </div>
   </>
  )
}

export default Login