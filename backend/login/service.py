# Import hmac.
import hmac
# Import os.
import os
# Import secrets.
import secrets
# Import urlencode, urlparse.
from urllib.parse import urlencode, urlparse

# Import load_dotenv.
from dotenv import load_dotenv
# Import HTTPException, Request.
from fastapi import HTTPException, Request
# Import RedirectResponse.
from fastapi.responses import RedirectResponse

# Import TokenRequest, get_tokens.
from spotify.web_api import TokenRequest, get_tokens

# Call load_dotenv.
load_dotenv()

# Set SPOTIFY_AUTHORIZE_URL.
SPOTIFY_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
# Set STATE_COOKIE.
STATE_COOKIE = "spotify_oauth_state"
# Set SPOTIFY_SCOPES.
SPOTIFY_SCOPES = (
    "user-read-private user-read-email playlist-read-private "
    "playlist-modify-private playlist-modify-public "
    "playlist-read-collaborative"
)


# Define _spotify_config.
def _spotify_config() -> tuple[str, str, str]:
    # Read client_id from server configuration.
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    # Read client_secret from server configuration.
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    # Read redirect_uri from server configuration.
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")
    # Check not client_id or not client_secret or (not redirect_uri).
    if not client_id or not client_secret or not redirect_uri:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(
            status_code=503,
            detail="Spotify OAuth is not configured. Set the Spotify environment variables.",
        )
    # Return the assembled result to the caller.
    return client_id, client_secret, redirect_uri


# Define spotify_login.
def spotify_login() -> RedirectResponse:
    # Set (client_id, _, redirect_uri).
    client_id, _, redirect_uri = _spotify_config()
    # Set state.
    state = secrets.token_urlsafe(32)
    # Set query.
    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "scope": SPOTIFY_SCOPES,
            "redirect_uri": redirect_uri,
            "state": state,
        }
    )
    # Set response.
    response = RedirectResponse(f"{SPOTIFY_AUTHORIZE_URL}?{query}")
    # Call response.set_cookie.
    response.set_cookie(
        key=STATE_COOKIE,
        value=state,
        max_age=600,
        httponly=True,
        secure=urlparse(redirect_uri).scheme == "https",
        samesite="lax",
        path="/",
    )
    # Return response.
    return response


# Define callback as an awaited operation.
async def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    # Check error.
    if error:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(status_code=400, detail=f"Spotify authorization failed: {error}")
    # Check not code.
    if not code:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(status_code=400, detail="Spotify did not provide an authorization code.")

    # Call validate_oauth_state.
    validate_oauth_state(request, state)
    # Wait for the operation and keep token_data.
    token_data = await get_tokens(TokenRequest(grant_type="authorization_code", code=code, state=state))
    # Read frontend_callback from server configuration.
    frontend_callback = os.getenv("FRONTEND_CALLBACK_URL", "http://localhost:5173/auth/callback")
    # Set payload.
    payload = {
        "access_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "token_type": token_data.get("token_type"),
        "expires_in": token_data.get("expires_in"),
        "scope": token_data.get("scope"),
    }

    # Fragment values are not sent to the frontend server in HTTP requests/logs.
    response = RedirectResponse(f"{frontend_callback}#{urlencode(payload)}")
    # Set response.headers['Cache-Control'].
    response.headers["Cache-Control"] = "no-store"
    # Set response.headers['Referrer-Policy'].
    response.headers["Referrer-Policy"] = "no-referrer"
    # Call response.delete_cookie.
    response.delete_cookie(key=STATE_COOKIE, path="/")
    # Return response.
    return response


# Define validate_oauth_state.
def validate_oauth_state(request: Request, state: str | None) -> None:
    # Set expected_state.
    expected_state = request.cookies.get(STATE_COOKIE)
    # Check not state or not expected_state or (not hmac.compare_digest(state, expected....
    if not state or not expected_state or not hmac.compare_digest(state, expected_state):
        # Stop this request with an explicit HTTP error.
        raise HTTPException(status_code=400, detail="Invalid or expired Spotify OAuth state.")

# File summary
# - Starts Spotify authorization with a short-lived state cookie.
# - Validates callbacks and exchanges codes on the server.
# - Redirects token fields to the frontend callback fragment.
