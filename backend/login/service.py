import hmac
import os
import secrets
from urllib.parse import urlencode, urlparse

from dotenv import load_dotenv
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from spotify.web_api import TokenRequest, get_tokens

load_dotenv()

SPOTIFY_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
STATE_COOKIE = "spotify_oauth_state"
SPOTIFY_SCOPES = (
    "user-read-private user-read-email playlist-read-private "
    "playlist-modify-private playlist-modify-public "
    "playlist-read-collaborative"
)


def _spotify_config() -> tuple[str, str, str]:
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")
    if not client_id or not client_secret or not redirect_uri:
        raise HTTPException(
            status_code=503,
            detail="Spotify OAuth is not configured. Set the Spotify environment variables.",
        )
    return client_id, client_secret, redirect_uri


def spotify_login() -> RedirectResponse:
    client_id, _, redirect_uri = _spotify_config()
    state = secrets.token_urlsafe(32)
    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "scope": SPOTIFY_SCOPES,
            "redirect_uri": redirect_uri,
            "state": state,
        }
    )
    response = RedirectResponse(f"{SPOTIFY_AUTHORIZE_URL}?{query}")
    response.set_cookie(
        key=STATE_COOKIE,
        value=state,
        max_age=600,
        httponly=True,
        secure=urlparse(redirect_uri).scheme == "https",
        samesite="lax",
        path="/",
    )
    return response


async def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    if error:
        raise HTTPException(status_code=400, detail=f"Spotify authorization failed: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Spotify did not provide an authorization code.")

    validate_oauth_state(request, state)
    token_data = await get_tokens(TokenRequest(grant_type="authorization_code", code=code, state=state))
    frontend_callback = os.getenv("FRONTEND_CALLBACK_URL", "http://localhost:5173/auth/callback")
    payload = {
        "access_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "token_type": token_data.get("token_type"),
        "expires_in": token_data.get("expires_in"),
        "scope": token_data.get("scope"),
    }

    # Fragment values are not sent to the frontend server in HTTP requests/logs.
    response = RedirectResponse(f"{frontend_callback}#{urlencode(payload)}")
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.delete_cookie(key=STATE_COOKIE, path="/")
    return response


def validate_oauth_state(request: Request, state: str | None) -> None:
    expected_state = request.cookies.get(STATE_COOKIE)
    if not state or not expected_state or not hmac.compare_digest(state, expected_state):
        raise HTTPException(status_code=400, detail="Invalid or expired Spotify OAuth state.")
