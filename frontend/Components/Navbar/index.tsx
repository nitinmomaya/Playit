import React from 'react'

const Navbar = () => {
  const logout = () => {
    localStorage.removeItem("spotify_access_token");
    localStorage.removeItem("spotify_refresh_token");
    localStorage.removeItem("spotify_token_type");
    localStorage.removeItem("spotify_expires_in");
    localStorage.removeItem("spotify_scope");
    localStorage.removeItem("spotify_user");

    window.location.href = "/login";
  };
  return (
    <>
      <div>Navbar</div>
      <button onClick={logout}>Logout</button>
    </>
  );
}

export default Navbar