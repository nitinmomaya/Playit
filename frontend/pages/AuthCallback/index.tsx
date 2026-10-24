// Use React state/lifecycle APIs.
import { useEffect } from "react";
// Use client-side routing and navigation.
import { useNavigate } from "react-router-dom";

// Import auth dependencies.
import { useSpotifyAuthActions } from "../../src/lib/auth";
// Import spotifyApi dependencies.
import { getSpotifyUser } from "../../src/lib/spotifyApi";

// Read callback/query values into AuthCallback.
const AuthCallback = () => {
  // Prepare navigate for the following operation.
  const navigate = useNavigate();
  // Prepare { setAuth, clearAuth } for the following operation.
  const { setAuth, clearAuth } = useSpotifyAuthActions();

  // Remove credential/error fragments from the address bar.
  useEffect(() => {
    // Read callback/query values into params.
    const params = new URLSearchParams(window.location.hash.slice(1));
    // Prepare accessToken for the following operation.
    const accessToken = params.get("access_token");
    // Prepare refreshToken for the following operation.
    const refreshToken = params.get("refresh_token");
    // Prepare tokenType for the following operation.
    const tokenType = params.get("token_type");
    // Prepare expiresIn for the following operation.
    const expiresIn = params.get("expires_in");
    // Prepare scope for the following operation.
    const scope = params.get("scope");
    // Prepare cancelled for the following operation.
    let cancelled = false;
    // Check accessToken && refreshToken && tokenType && expiresIn.
    if (accessToken && refreshToken && tokenType && expiresIn) {
      // Call setAuth.
      setAuth({
        // Set the access_token option/value.
        access_token: accessToken,
        // Set the refresh_token option/value.
        refresh_token: refreshToken,
        // Set the token_type option/value.
        token_type: tokenType,
        // Set the expires_in option/value.
        expires_in: expiresIn,
        scope,
        // Set the profile option/value.
        profile: null,
      });
      // StrictMode may replay the effect; clear credentials after it settles.
      void getSpotifyUser().then((profile) => {
        // Check cancelled.
        if (cancelled) return;
        // Remove credential/error fragments from the address bar.
        window.history.replaceState(null, "", window.location.pathname);
        // Call setAuth.
        setAuth({ profile });
        // Navigate after the auth or request result is known.
        navigate("/", { replace: true });
      }).catch(() => {
        // Check cancelled.
        if (cancelled) return;
        // Remove credential/error fragments from the address bar.
        window.history.replaceState(null, "", window.location.pathname);
        // Call clearAuth.
        clearAuth();
        // Navigate after the auth or request result is known.
        navigate("/login", { replace: true });
      });
    } else {
      // Call clearAuth.
      clearAuth();
      // Navigate after the auth or request result is known.
      navigate("/login", { replace: true });
    }
    // Return the current operation's result.
    return () => { cancelled = true; };
  }, [navigate, setAuth, clearAuth]);

  // Render the component UI.
  return <p>Signing you in...</p>;
};

// Export this module's public entry point.
export default AuthCallback;

/* File summary
 * - Reads Spotify credentials from the callback fragment.
 * - Fetches the profile, clears the fragment, and opens Home.
 */
