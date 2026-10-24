"""Server-side Google token exchange and YouTube API calls.

Mirrors spotify/web_api.py without sharing provider credentials or models.
"""

# Import os.
import os
# Import re.
import re
# Import ssl.
import ssl
# Import Any, Literal.
from typing import Any, Literal

# Import httpx.
import httpx
# Import truststore.
import truststore
# Import load_dotenv.
from dotenv import load_dotenv
# Import HTTPException.
from fastapi import HTTPException
# Import BaseModel, Field, model_validator.
from pydantic import BaseModel, Field, model_validator

# Call load_dotenv.
load_dotenv()

# Set GOOGLE_TOKEN_URL.
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
# Set GOOGLE_USERINFO_URL.
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
# Set YOUTUBE_API_URL.
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3"


# Define _ssl_context.
def _ssl_context() -> ssl.SSLContext:
    # Set context.
    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    # Read (ca_file, ca_dir) from server configuration.
    ca_file, ca_dir = os.getenv("SSL_CERT_FILE"), os.getenv("SSL_CERT_DIR")
    # Check ca_file or ca_dir.
    if ca_file or ca_dir:
        # Call context.load_verify_locations.
        context.load_verify_locations(cafile=ca_file, capath=ca_dir)
    # Return context.
    return context


# Define oauth_config.
def oauth_config() -> tuple[str, str, str]:
    # Read client_id from server configuration.
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    # Read client_secret from server configuration.
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    # Read redirect_uri from server configuration.
    redirect_uri = os.getenv("YOUTUBE_REDIRECT_URI")
    # Check not client_id or not client_secret or (not redirect_uri).
    if not client_id or not client_secret or not redirect_uri:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(503, "YouTube OAuth is not configured. Set GOOGLE_CLIENT_ID, "
                            "GOOGLE_CLIENT_SECRET, and YOUTUBE_REDIRECT_URI.")
    # Return the assembled result to the caller.
    return client_id, client_secret, redirect_uri


# Group the fields/behavior of TokenRequest.
class TokenRequest(BaseModel):
    # Declare grant_type.
    grant_type: Literal["authorization_code", "refresh_token"]
    # Validate/configure code.
    code: str | None = Field(default=None, min_length=1)
    # Validate/configure state.
    state: str | None = Field(default=None, min_length=1)
    # Validate/configure refresh_token.
    refresh_token: str | None = Field(default=None, min_length=1)

    # Define validate_grant.
    @model_validator(mode="after")
    def validate_grant(self) -> "TokenRequest":
        # Check self.grant_type == 'authorization_code' and (not self.code or not self.state).
        if self.grant_type == "authorization_code" and (not self.code or not self.state):
            # Propagate this failure instead of continuing.
            raise ValueError("code and state are required for authorization_code")
        # Check self.grant_type == 'refresh_token' and (not self.refresh_token).
        if self.grant_type == "refresh_token" and not self.refresh_token:
            # Propagate this failure instead of continuing.
            raise ValueError("refresh_token is required for refresh_token")
        # Return self.
        return self


class CreatePlaylist(BaseModel):
    """Playlist metadata; private by default, like Spotify's safe defaults."""

    # Validate/configure name.
    name: str = Field(min_length=1, max_length=150, pattern=r"\S")
    # Validate/configure description.
    description: str = Field(default="", max_length=5000)
    # Declare privacy_status.
    privacy_status: Literal["private", "unlisted", "public"] = "private"


class UpdatePlaylist(BaseModel):
    """Replace title/description; preserve privacy unless explicitly supplied."""

    # Validate/configure name.
    name: str = Field(min_length=1, max_length=150, pattern=r"\S")
    # Validate/configure description.
    description: str = Field(default="", max_length=5000)
    # Declare privacy_status.
    privacy_status: Literal["private", "unlisted", "public"] | None = None


# Group the fields/behavior of AddItemRequest.
class AddItemRequest(BaseModel):
    # YouTube inserts ONE video per request, unlike Spotify's URI batches.
    video_id: str = Field(pattern=r"^[A-Za-z0-9_-]{11}$")
    # Validate/configure position.
    position: int | None = Field(default=None, ge=0)


# Define _request_json as an awaited operation.
async def _request_json(
    client: httpx.AsyncClient, method: str, url: str, **kwargs: Any,
) -> dict[str, Any]:
    # Handle failures from this operation below.
    try:
        # Wait for the operation and keep response.
        response = await client.request(method, url, **kwargs)
    except httpx.TimeoutException as exc:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(504, "Google/YouTube request timed out.") from exc
    except httpx.RequestError as exc:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(502, "Could not connect to Google/YouTube.") from exc
    # Check response.is_error.
    if response.is_error:
        # Set headers.
        headers = {}
        # Check response.status_code == 429 and 'Retry-After' in response.headers.
        if response.status_code == 429 and "Retry-After" in response.headers:
            # Set headers['Retry-After'].
            headers["Retry-After"] = response.headers["Retry-After"]
        # Set detail.
        detail = "Google/YouTube rejected the request. Check the token, granted permissions, enabled API, quota, or request parameters."
        # Map known OAuth codes to fixed messages; never expose Google's raw
        # response, which may contain sensitive request information.
        if url == GOOGLE_TOKEN_URL:
            # Handle failures from this operation below.
            try:
                # Set payload.
                payload = response.json()
            except ValueError:
                # Set payload.
                payload = {}
            # Set oauth_error.
            oauth_error = payload.get("error") if isinstance(payload, dict) else None
            # Set messages.
            messages = {
                "invalid_client": "Google rejected the OAuth client. Check that GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET belong to the same Web application client.",
                "invalid_grant": "Google rejected the authorization code or PKCE verifier. Start login again; do not reload or reuse the callback URL.",
                "redirect_uri_mismatch": "The YouTube redirect URI does not match the URI registered for this Google OAuth client.",
                "access_denied": "Google denied access. Check the consent screen, test users, and account permissions.",
            }
            # Check isinstance(oauth_error, str).
            if isinstance(oauth_error, str):
                # Set detail.
                detail = messages.get(oauth_error, detail)
        # Check url.startswith(f'{YOUTUBE_API_URL}/').
        elif url.startswith(f"{YOUTUBE_API_URL}/"):
            # Handle failures from this operation below.
            try:
                # Set body.
                body = response.json()
            except ValueError:
                # Set body.
                body = {}
            # Set error.
            error = body.get("error", {}) if isinstance(body, dict) else {}
            # Declare reasons.
            reasons: set[str] = set()
            # Check isinstance(error, dict).
            if isinstance(error, dict):
                # Process each entry in error.get('errors', []) or [].
                for entry in error.get("errors", []) or []:
                    # Check isinstance(entry, dict) and isinstance(entry.get('reason'), str).
                    if isinstance(entry, dict) and isinstance(entry.get("reason"), str):
                        # Call reasons.add.
                        reasons.add(entry["reason"])
                # Process each entry in error.get('details', []) or [].
                for entry in error.get("details", []) or []:
                    # Check isinstance(entry, dict) and isinstance(entry.get('reason'), str).
                    if isinstance(entry, dict) and isinstance(entry.get("reason"), str):
                        # Call reasons.add.
                        reasons.add(entry["reason"])
            # Check reasons & {'accessNotConfigured', 'SERVICE_DISABLED'}.
            if reasons & {"accessNotConfigured", "SERVICE_DISABLED"}:
                # Set detail.
                detail = "YouTube Data API v3 is disabled in the Google Cloud project owning this OAuth client. Enable it in APIs & Services, then retry."
            # Check reasons & {'insufficientPermissions', 'ACCESS_TOKEN_SCOPE_INSUFFICIENT'}.
            elif reasons & {"insufficientPermissions", "ACCESS_TOKEN_SCOPE_INSUFFICIENT"}:
                # Set detail.
                detail = "The required YouTube permission was not granted. Reconnect and grant YouTube access; playlist writes require youtube.force-ssl (or youtube), not youtube.readonly. Refreshing cannot add permissions."
            # Check reasons & {'quotaExceeded', 'dailyLimitExceeded', 'rateLimitExceeded', 'RAT....
            elif reasons & {"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded", "RATE_LIMIT_EXCEEDED"}:
                # Set detail.
                detail = "The Google Cloud project's YouTube API quota or rate limit was exceeded. Retry after the limit resets or review the project's quota."
            # Check reasons & {'youtubeSignupRequired', 'channelNotFound'}.
            elif reasons & {"youtubeSignupRequired", "channelNotFound"}:
                # Set detail.
                detail = "No usable YouTube channel was found for this account. Open YouTube, create or select a channel, then reconnect."
            # Check response.status_code == 401.
            elif response.status_code == 401:
                # Set detail.
                detail = "Your Google access token expired or was revoked. Refresh access or reconnect YouTube."
        # Stop this request with an explicit HTTP error.
        raise HTTPException(
            response.status_code if response.status_code < 500 else 502,
            detail, headers=headers,
        )
    # Check response.status_code == 204.
    if response.status_code == 204:
        # Return the assembled result to the caller.
        return {}
    # Handle failures from this operation below.
    try:
        # Set payload.
        payload = response.json()
    except ValueError as exc:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(502, "Google/YouTube returned invalid JSON.") from exc
    # Check not isinstance(payload, dict).
    if not isinstance(payload, dict):
        # Stop this request with an explicit HTTP error.
        raise HTTPException(502, "Google/YouTube returned an invalid response.")
    # Return payload.
    return payload


# Define get_tokens as an awaited operation.
async def get_tokens(request: TokenRequest, code_verifier: str | None = None) -> dict[str, Any]:
    # Set (client_id, client_secret, redirect_uri).
    client_id, client_secret, redirect_uri = oauth_config()
    # Set data.
    data = {"client_id": client_id, "client_secret": client_secret,
            "grant_type": request.grant_type}
    # Check request.grant_type == 'authorization_code'.
    if request.grant_type == "authorization_code":
        # Check not code_verifier.
        if not code_verifier:
            # Stop this request with an explicit HTTP error.
            raise HTTPException(400, "Missing OAuth verifier. Start YouTube login again.")
        # Call data.update.
        data.update(code=request.code or "", redirect_uri=redirect_uri, code_verifier=code_verifier)
    else:
        # Set data['refresh_token'].
        data["refresh_token"] = request.refresh_token or ""
    # Manage httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) with automatic cleanup.
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        # Wait for the operation and keep payload.
        payload = await _request_json(client, "POST", GOOGLE_TOKEN_URL, data=data)
    # Check not isinstance(payload.get('access_token'), str) or not payload['access_tok....
    if not isinstance(payload.get("access_token"), str) or not payload["access_token"]:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(502, "Google did not return an access token.")
    # Do not forward ID tokens or unexpected upstream fields as application identity.
    tokens = {key: payload[key] for key in
              ("access_token", "refresh_token", "token_type", "expires_in", "scope") if key in payload}
    # Check request.grant_type == 'refresh_token' and (not tokens.get('refresh_token')).
    if request.grant_type == "refresh_token" and not tokens.get("refresh_token"):
        # Set tokens['refresh_token'].
        tokens["refresh_token"] = request.refresh_token
    # Return tokens.
    return tokens


async def get_user(access_token: str) -> dict[str, Any]:
    """Google account profile, not the user's YouTube channel."""
    # Manage httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) with automatic cleanup.
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        # Return await _request_json(client, 'GET', GOOGLE_USERINFO_URL, headers={'Authoriza....
        return await _request_json(client, "GET", GOOGLE_USERINFO_URL,
                                   headers={"Authorization": f"Bearer {access_token}"})


# Define _get_collection as an awaited operation.
async def _get_collection(
    resource: Literal["channels", "playlists"], access_token: str,
    page_token: str | None, max_results: int,
) -> dict[str, Any]:
    # Declare params.
    params: dict[str, str | int] = {
        "part": "snippet,contentDetails" if resource == "channels" else "snippet,status,contentDetails",
        "mine": "true", "maxResults": max_results,
    }
    # Check page_token.
    if page_token:
        # Set params['pageToken'].
        params["pageToken"] = page_token
    # Manage httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) with automatic cleanup.
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        # Wait for the operation and keep payload.
        payload = await _request_json(
            client, "GET", f"{YOUTUBE_API_URL}/{resource}", params=params,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    # YouTube can omit items on a successful, explicitly empty page (for
    # example channels.list mine=true for an account without a channel).
    # Keep rejecting malformed non-empty responses rather than masking them.
    page_info = payload.get("pageInfo")
    # Check 'items' not in payload and isinstance(page_info, dict) and (page_info.get('....
    if "items" not in payload and isinstance(page_info, dict) and page_info.get("totalResults") == 0:
        # Set payload['items'].
        payload["items"] = []
    # Set items.
    items = payload.get("items")
    # Check not isinstance(items, list) or any((not isinstance(item, dict) for item in ....
    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
        # Stop this request with an explicit HTTP error.
        raise HTTPException(502, "YouTube returned an invalid collection.")
    # Native page tokens keep calls/quota bounded; never follow upstream URLs.
    return payload


# Define get_channels as an awaited operation.
async def get_channels(access_token: str, page_token: str | None = None,
                       max_results: int = 50) -> dict[str, Any]:
    # Return await _get_collection('channels', access_token, page_token, max_results).
    return await _get_collection("channels", access_token, page_token, max_results)


# Define get_user_playlists as an awaited operation.
async def get_user_playlists(access_token: str, page_token: str | None = None,
                             max_results: int = 50) -> dict[str, Any]:
    # Return await _get_collection('playlists', access_token, page_token, max_results).
    return await _get_collection("playlists", access_token, page_token, max_results)


async def search_videos(query: str, access_token: str) -> list[dict[str, Any]]:
    """One bounded search + metadata lookup per recommendation; no pagination.

    Only playable-looking music videos are candidates. YouTube search consumes
    quota, so do not automatically retry searches or fan out query variants.
    """
    # Set headers.
    headers = {"Authorization": f"Bearer {access_token}"}
    # Manage httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) with automatic cleanup.
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        # Wait for the operation and keep results.
        results = await _request_json(
            client, "GET", f"{YOUTUBE_API_URL}/search",
            params={"part": "snippet", "q": query, "type": "video",
                    "videoCategoryId": "10", "maxResults": 5}, headers=headers,
        )
        # Set ids.
        ids = [item.get("id", {}).get("videoId") for item in results.get("items", [])
               if isinstance(item, dict) and isinstance(item.get("id"), dict)]
        # Set ids.
        ids = [value for value in ids if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{11}", value)]
        # Check not ids.
        if not ids:
            # Return the assembled result to the caller.
            return []
        # Wait for the operation and keep videos.
        videos = await _request_json(
            client, "GET", f"{YOUTUBE_API_URL}/videos",
            params={"part": "snippet,contentDetails,status", "id": ",".join(ids)}, headers=headers,
        )
    # Set items.
    items = videos.get("items", [])
    # Check not isinstance(items, list).
    if not isinstance(items, list):
        # Stop this request with an explicit HTTP error.
        raise HTTPException(502, "YouTube returned invalid video metadata.")
    # Set playable.
    playable = [item for item in items if isinstance(item, dict) and item.get("id") in ids
            and isinstance(item.get("snippet"), dict)
            and isinstance(item["snippet"].get("title"), str)
            and item.get("snippet", {}).get("liveBroadcastContent", "none") == "none"
            and item.get("status", {}).get("uploadStatus") == "processed"
            and item.get("status", {}).get("privacyStatus") == "public"]
    # videos.list need not preserve search ranking. Restore it explicitly so
    # first-best tie selection follows the original search result order.
    return sorted(playable, key=lambda item: ids.index(item["id"]))


# Define create_playlist as an awaited operation.
async def create_playlist(request: CreatePlaylist, access_token: str) -> dict[str, Any]:
    # Set body.
    body = {
        "snippet": {"title": request.name, "description": request.description},
        "status": {"privacyStatus": request.privacy_status},
    }
    # Manage httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) with automatic cleanup.
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        # Never automatically retry writes: a timeout may follow a successful write.
        return await _request_json(
            client, "POST", f"{YOUTUBE_API_URL}/playlists",
            params={"part": "snippet,status"}, json=body,
            headers={"Authorization": f"Bearer {access_token}"},
        )


# Define update_playlist as an awaited operation.
async def update_playlist(playlist_id: str, request: UpdatePlaylist,
                          access_token: str) -> dict[str, Any]:
    # Read before writing to retain snippet fields this API does not expose.
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        # Set headers.
        headers = {"Authorization": f"Bearer {access_token}"}
        # Wait for the operation and keep current.
        current = await _request_json(
            client, "GET", f"{YOUTUBE_API_URL}/playlists",
            params={"part": "snippet", "id": playlist_id}, headers=headers,
        )
        # Set items.
        items = current.get("items", [])
        # Check not isinstance(items, list) or not items.
        if not isinstance(items, list) or not items:
            # Stop this request with an explicit HTTP error.
            raise HTTPException(404, "YouTube playlist not found or inaccessible.")
        # Set snippet.
        snippet = items[0].get("snippet", {})
        # Set preserved.
        preserved = {key: snippet[key] for key in ("tags", "defaultLanguage") if key in snippet}
        # Declare body.
        body: dict[str, Any] = {
            "id": playlist_id,
            "snippet": {**preserved, "title": request.name, "description": request.description},
        }
        # Set part.
        part = "snippet"
        # Check request.privacy_status is not None.
        if request.privacy_status is not None:
            # Set body['status'].
            body["status"] = {"privacyStatus": request.privacy_status}
            # Update part.
            part += ",status"
        # Return await _request_json(client, 'PUT', f'{YOUTUBE_API_URL}/playlists', params={....
        return await _request_json(
            client, "PUT", f"{YOUTUBE_API_URL}/playlists",
            params={"part": part}, json=body, headers=headers,
        )


# Define delete_playlist as an awaited operation.
async def delete_playlist(playlist_id: str, access_token: str) -> None:
    # Manage httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) with automatic cleanup.
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        # Wait for _request_json(client, 'DELETE', f'{YOUTUBE_API_URL}/playlists', params={'id....
        await _request_json(
            client, "DELETE", f"{YOUTUBE_API_URL}/playlists",
            params={"id": playlist_id}, headers={"Authorization": f"Bearer {access_token}"},
        )


# Define add_item_to_playlist as an awaited operation.
async def add_item_to_playlist(playlist_id: str, request: AddItemRequest,
                               access_token: str) -> dict[str, Any]:
    # Declare snippet.
    snippet: dict[str, Any] = {
        "playlistId": playlist_id,
        "resourceId": {"kind": "youtube#video", "videoId": request.video_id},
    }
    # Check request.position is not None.
    if request.position is not None:
        # Set snippet['position'].
        snippet["position"] = request.position
    # Manage httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) with automatic cleanup.
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        # Return await _request_json(client, 'POST', f'{YOUTUBE_API_URL}/playlistItems', par....
        return await _request_json(
            client, "POST", f"{YOUTUBE_API_URL}/playlistItems",
            params={"part": "snippet"}, json={"snippet": snippet},
            headers={"Authorization": f"Bearer {access_token}"},
        )


# Define remove_item_from_playlist as an awaited operation.
async def remove_item_from_playlist(playlist_item_id: str, access_token: str) -> None:
    # This is the playlist-item ID returned by insertion, NOT the video ID.
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        # Wait for _request_json(client, 'DELETE', f'{YOUTUBE_API_URL}/playlistItems', params=....
        await _request_json(
            client, "DELETE", f"{YOUTUBE_API_URL}/playlistItems",
            params={"id": playlist_item_id}, headers={"Authorization": f"Bearer {access_token}"},
        )

# File summary
# - Calls Google tokens/userinfo and the official YouTube Data API.
# - Maps known OAuth, permission, channel, and quota errors.
# - Searches videos and performs explicit playlist/item operations.
