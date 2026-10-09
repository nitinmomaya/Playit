import json
import random
import hmac
import os
import secrets
from urllib.parse import urlencode, urlparse

import httpx
from dotenv import load_dotenv
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

load_dotenv()

SPOTIFY_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_PROFILE_URL = "https://api.spotify.com/v1/me"
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
) -> JSONResponse:
    if error:
        raise HTTPException(status_code=400, detail=f"Spotify authorization failed: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Spotify did not provide an authorization code.")

    expected_state = request.cookies.get(STATE_COOKIE)
    if not state or not expected_state or not hmac.compare_digest(state, expected_state):
        raise HTTPException(status_code=400, detail="Invalid or expired Spotify OAuth state.")

    client_id, client_secret, redirect_uri = _spotify_config()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_response = await client.post(
                SPOTIFY_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                auth=(client_id, client_secret),
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise HTTPException(
                    status_code=502,
                    detail="Spotify token response did not include an access token.",
                )

            profile_response = await client.get(
                SPOTIFY_PROFILE_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            profile_response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail="Spotify rejected the authorization or profile request.",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Could not connect to Spotify.") from exc

    profile_data = profile_response.json()
    frontend_callback = "http://localhost:5173/auth/callback"
    payload = {
        "access_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "token_type": token_data.get("token_type"),
        "expires_in": token_data.get("expires_in"),
        "scope": token_data.get("scope"),
        "profile": json.dumps(profile_data),
    }

    response = RedirectResponse(f"{frontend_callback}?{urlencode(payload)}")
    response.delete_cookie(key=STATE_COOKIE, path="/")
    return response
