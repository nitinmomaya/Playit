"""OAuth redirects and browser-state checks, analogous to login/service.py."""

# Import base64.
import base64
# Import hashlib.
import hashlib
# Import hmac.
import hmac
# Import os.
import os
# Import secrets.
import secrets
# Import urlencode, urlparse.
from urllib.parse import urlencode, urlparse

# Import HTTPException, Request, Response.
from fastapi import HTTPException, Request, Response
# Import RedirectResponse.
from fastapi.responses import RedirectResponse

# Import TokenRequest, get_tokens, oauth_config.
from youtube.web_api import TokenRequest, get_tokens, oauth_config

# Set GOOGLE_AUTHORIZE_URL.
GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
# Set STATE_COOKIE.
STATE_COOKIE = "youtube_oauth_state"
# Set VERIFIER_COOKIE.
VERIFIER_COOKIE = "youtube_oauth_verifier"
# Set YOUTUBE_SCOPES.
YOUTUBE_SCOPES = "openid email profile https://www.googleapis.com/auth/youtube.force-ssl"


# Define no_store.
def no_store(response: Response) -> None:
    # Set response.headers['Cache-Control'].
    response.headers["Cache-Control"] = "no-store"
    # Set response.headers['Pragma'].
    response.headers["Pragma"] = "no-cache"
    # Set response.headers['Referrer-Policy'].
    response.headers["Referrer-Policy"] = "no-referrer"


# Define clear_oauth_cookies.
def clear_oauth_cookies(response: Response) -> None:
    # Process each name in (STATE_COOKIE, VERIFIER_COOKIE).
    for name in (STATE_COOKIE, VERIFIER_COOKIE):
        # Call response.delete_cookie.
        response.delete_cookie(name, path="/youtube")


# Define youtube_login.
def youtube_login() -> RedirectResponse:
    # Set (client_id, _, redirect_uri).
    client_id, _, redirect_uri = oauth_config()
    # Set (state, verifier).
    state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(64)
    # Set challenge.
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    # Set query.
    query = urlencode({
        "client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code",
        "scope": YOUTUBE_SCOPES, "state": state, "access_type": "offline",
        "include_granted_scopes": "true", "code_challenge": challenge,
        "code_challenge_method": "S256", "prompt": "consent select_account",
    })
    # Set response.
    response = RedirectResponse(f"{GOOGLE_AUTHORIZE_URL}?{query}")
    # Process each (name, value) in ((STATE_COOKIE, state), (VERIFIER_COOKIE, verifier)).
    for name, value in ((STATE_COOKIE, state), (VERIFIER_COOKIE, verifier)):
        # Call response.set_cookie.
        response.set_cookie(name, value, max_age=600, httponly=True,
                            secure=urlparse(redirect_uri).scheme == "https",
                            samesite="lax", path="/youtube")
    # Call no_store.
    no_store(response)
    # Return response.
    return response


# Define validate_oauth_state.
def validate_oauth_state(request: Request, state: str | None) -> str:
    # Set expected.
    expected = request.cookies.get(STATE_COOKIE)
    # Set verifier.
    verifier = request.cookies.get(VERIFIER_COOKIE)
    # Check not state or not expected or (not hmac.compare_digest(state, expected)) or ....
    if not state or not expected or not hmac.compare_digest(state, expected) or not verifier:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(400, "Invalid or expired YouTube OAuth state. Start login again.")
    # Return verifier.
    return verifier


async def callback(request: Request, code: str | None = None, state: str | None = None,
                   error: str | None = None) -> RedirectResponse:
    """Mirror Spotify's frontend handoff; never include ID tokens or secrets.

    Credentials are passed in a fragment, not a query string, and kept only in
    browser memory. This is not a persisted server-side Playit login session.
    """
    # Read frontend_callback from server configuration.
    frontend_callback = os.getenv(
        "YOUTUBE_FRONTEND_CALLBACK_URL", "http://localhost:5173/auth/youtube/callback",
    )
    # Handle failures from this operation below.
    try:
        # Set verifier.
        verifier = validate_oauth_state(request, state)
        # Check error.
        if error:
            # Stop this request with an explicit HTTP error.
            raise HTTPException(400, "YouTube authorization was denied or failed.")
        # Check not code.
        if not code:
            # Stop this request with an explicit HTTP error.
            raise HTTPException(400, "Google did not provide an authorization code.")
        # Wait for the operation and keep tokens.
        tokens = await get_tokens(TokenRequest(grant_type="authorization_code", code=code, state=state), verifier)
        # Set response.
        response = RedirectResponse(f"{frontend_callback}#{urlencode(tokens)}")
    except HTTPException as exc:
        # Only our fixed, sanitized messages are handed to the frontend.
        failure = urlencode({"error": "youtube_authorization_failed", "error_description": str(exc.detail)})
        # Set response.
        response = RedirectResponse(f"{frontend_callback}#{failure}")
    # Call no_store.
    no_store(response)
    # Call clear_oauth_cookies.
    clear_oauth_cookies(response)
    # Return response.
    return response

# File summary
# - Starts Google OAuth using state cookies and S256 PKCE.
# - Validates authorization callbacks and exchanges codes.
# - Clears cookies and hands filtered tokens/errors to the frontend.
