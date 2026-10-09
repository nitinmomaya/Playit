import React from 'react'

const Login = () => {

    const handleSpotifyLogin=()=>{
        window.location.href='http://127.0.0.1:8000/login'
    }
  return (
   <>
   <h1>Login</h1>
   <button onClick={handleSpotifyLogin}>Login with Spotify</button>
   </>
  )
}

export default Login