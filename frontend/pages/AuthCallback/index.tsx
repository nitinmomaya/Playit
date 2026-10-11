import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { useSpotifyAuthActions } from "../../src/lib/auth";
import { getSpotifyUser } from "../../src/lib/spotifyApi";

const AuthCallback = () => {
  const navigate = useNavigate();
  const { setAuth, clearAuth } = useSpotifyAuthActions();

  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.slice(1));
    const accessToken = params.get("access_token");
    const refreshToken = params.get("refresh_token");
    const tokenType = params.get("token_type");
    const expiresIn = params.get("expires_in");
    const scope = params.get("scope");
    let cancelled = false;
    if (accessToken && refreshToken && tokenType && expiresIn) {
      setAuth({
        access_token: accessToken,
        refresh_token: refreshToken,
        token_type: tokenType,
        expires_in: expiresIn,
        scope,
        profile: null,
      });
      // StrictMode may replay the effect; clear credentials after it settles.
      void getSpotifyUser().then((profile) => {
        if (cancelled) return;
        window.history.replaceState(null, "", window.location.pathname);
        setAuth({ profile });
        navigate("/", { replace: true });
      }).catch(() => {
        if (cancelled) return;
        window.history.replaceState(null, "", window.location.pathname);
        clearAuth();
        navigate("/login", { replace: true });
      });
    } else {
      clearAuth();
      navigate("/login", { replace: true });
    }
    return () => { cancelled = true; };
  }, [navigate, setAuth, clearAuth]);

  return <p>Signing you in...</p>;
};

export default AuthCallback;
