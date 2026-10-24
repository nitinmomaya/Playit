"""OAuth redirects and browser-state checks, analogous to login/service.py."""

import base64
import hashlib
import hmac
import os
import secrets
from urllib.parse import urlencode, urlparse

from fastapi import HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from youtube.web_api import TokenRequest, get_tokens, oauth_config

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
STATE_COOKIE = "youtube_oauth_state"
VERIFIER_COOKIE = "youtube_oauth_verifier"
YOUTUBE_SCOPES = "openid email profile https://www.googleapis.com/auth/youtube.force-ssl"


def no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Referrer-Policy"] = "no-referrer"


def clear_oauth_cookies(response: Response) -> None:
    for name in (STATE_COOKIE, VERIFIER_COOKIE):
        response.delete_cookie(name, path="/youtube")


def youtube_login() -> RedirectResponse:
    client_id, _, redirect_uri = oauth_config()
    state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    query = urlencode({
        "client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code",
        "scope": YOUTUBE_SCOPES, "state": state, "access_type": "offline",
        "include_granted_scopes": "true", "code_challenge": challenge,
        "code_challenge_method": "S256", "prompt": "consent select_account",
    })
    response = RedirectResponse(f"{GOOGLE_AUTHORIZE_URL}?{query}")
    for name, value in ((STATE_COOKIE, state), (VERIFIER_COOKIE, verifier)):
        response.set_cookie(name, value, max_age=600, httponly=True,
                            secure=urlparse(redirect_uri).scheme == "https",
                            samesite="lax", path="/youtube")
    no_store(response)
    return response


def validate_oauth_state(request: Request, state: str | None) -> str:
    expected = request.cookies.get(STATE_COOKIE)
    verifier = request.cookies.get(VERIFIER_COOKIE)
    if not state or not expected or not hmac.compare_digest(state, expected) or not verifier:
        raise HTTPException(400, "Invalid or expired YouTube OAuth state. Start login again.")
    return verifier


async def callback(request: Request, code: str | None = None, state: str | None = None,
                   error: str | None = None) -> RedirectResponse:
    """Mirror Spotify's frontend handoff; never include ID tokens or secrets.

    Credentials are passed in a fragment, not a query string, and kept only in
    browser memory. This is not a persisted server-side Playit login session.
    """
    frontend_callback = os.getenv(
        "YOUTUBE_FRONTEND_CALLBACK_URL", "http://localhost:5173/auth/youtube/callback",
    )
    try:
        verifier = validate_oauth_state(request, state)
        if error:
            raise HTTPException(400, "YouTube authorization was denied or failed.")
        if not code:
            raise HTTPException(400, "Google did not provide an authorization code.")
        tokens = await get_tokens(TokenRequest(grant_type="authorization_code", code=code, state=state), verifier)
        response = RedirectResponse(f"{frontend_callback}#{urlencode(tokens)}")
    except HTTPException as exc:
        # Only our fixed, sanitized messages are handed to the frontend.
        failure = urlencode({"error": "youtube_authorization_failed", "error_description": str(exc.detail)})
        response = RedirectResponse(f"{frontend_callback}#{failure}")
    no_store(response)
    clear_oauth_cookies(response)
    return response