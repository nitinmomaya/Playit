import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { useSpotifyAuthActions } from "../../src/lib/auth";

const AuthCallback = () => {
  const navigate = useNavigate();
  const { setAuth } = useSpotifyAuthActions();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const profileRaw = params.get("profile");
    const accessToken = params.get("access_token");
    const refreshToken = params.get("refresh_token");
    const tokenType = params.get("token_type");
    const expiresIn = params.get("expires_in");
    const scope = params.get("scope");
    let parsedProfile = null;
    if (profileRaw) {
      try {
        parsedProfile = JSON.parse(profileRaw);
      } catch {
        parsedProfile = { raw: profileRaw };
      }
    }

    if (accessToken && refreshToken && tokenType && expiresIn && scope) {
      console.log("accessToken", accessToken);
      setAuth({
        access_token: accessToken,
        refresh_token: refreshToken,
        token_type: tokenType,
        expires_in: expiresIn,
        scope,
        profile: parsedProfile,
      });
    }

    navigate("/", { replace: true });
  }, [navigate, setAuth]);

  return <p>Signing you in...</p>;
};

export default AuthCallback;
