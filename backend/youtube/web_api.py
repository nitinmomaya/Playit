"""Server-side Google token exchange and YouTube API calls.

Mirrors spotify/web_api.py without sharing provider credentials or models.
"""

import logging
import os
import re
import ssl
from typing import Any, Literal

import httpx
import truststore
from dotenv import load_dotenv
from fastapi import HTTPException
from pydantic import BaseModel, Field, model_validator

load_dotenv()

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3"
logger = logging.getLogger(__name__)


def _ssl_context() -> ssl.SSLContext:
    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ca_file, ca_dir = os.getenv("SSL_CERT_FILE"), os.getenv("SSL_CERT_DIR")
    if ca_file or ca_dir:
        context.load_verify_locations(cafile=ca_file, capath=ca_dir)
    return context


def oauth_config() -> tuple[str, str, str]:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("YOUTUBE_REDIRECT_URI")
    if not client_id or not client_secret or not redirect_uri:
        raise HTTPException(503, "YouTube OAuth is not configured. Set GOOGLE_CLIENT_ID, "
                            "GOOGLE_CLIENT_SECRET, and YOUTUBE_REDIRECT_URI.")
    return client_id, client_secret, redirect_uri


class TokenRequest(BaseModel):
    grant_type: Literal["authorization_code", "refresh_token"]
    code: str | None = Field(default=None, min_length=1)
    state: str | None = Field(default=None, min_length=1)
    refresh_token: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_grant(self) -> "TokenRequest":
        if self.grant_type == "authorization_code" and (not self.code or not self.state):
            raise ValueError("code and state are required for authorization_code")
        if self.grant_type == "refresh_token" and not self.refresh_token:
            raise ValueError("refresh_token is required for refresh_token")
        return self


class CreatePlaylist(BaseModel):
    """Playlist metadata; private by default, like Spotify's safe defaults."""

    name: str = Field(min_length=1, max_length=150, pattern=r"\S")
    description: str = Field(default="", max_length=5000)
    privacy_status: Literal["private", "unlisted", "public"] = "private"


class UpdatePlaylist(BaseModel):
    """Replace title/description; preserve privacy unless explicitly supplied."""

    name: str = Field(min_length=1, max_length=150, pattern=r"\S")
    description: str = Field(default="", max_length=5000)
    privacy_status: Literal["private", "unlisted", "public"] | None = None


class AddItemRequest(BaseModel):
    # YouTube inserts ONE video per request, unlike Spotify's URI batches.
    video_id: str = Field(pattern=r"^[A-Za-z0-9_-]{11}$")
    position: int | None = Field(default=None, ge=0)


async def _request_json(
    client: httpx.AsyncClient, method: str, url: str, **kwargs: Any,
) -> dict[str, Any]:
    try:
        response = await client.request(method, url, **kwargs)
    except httpx.TimeoutException as exc:
        raise HTTPException(504, "Google/YouTube request timed out.") from exc
    except httpx.RequestError as exc:
        raise HTTPException(502, "Could not connect to Google/YouTube.") from exc
    if response.is_error:
        headers = {}
        if response.status_code == 429 and "Retry-After" in response.headers:
            headers["Retry-After"] = response.headers["Retry-After"]
        detail = "Google/YouTube rejected the request. Check the token, granted permissions, enabled API, quota, or request parameters."
        # Map known OAuth codes to fixed messages; never expose Google's raw
        # response, which may contain sensitive request information.
        if url == GOOGLE_TOKEN_URL:
            try:
                payload = response.json()
            except ValueError:
                payload = {}
            oauth_error = payload.get("error") if isinstance(payload, dict) else None
            messages = {
                "invalid_client": "Google rejected the OAuth client. Check that GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET belong to the same Web application client.",
                "invalid_grant": "Google rejected the authorization code or PKCE verifier. Start login again; do not reload or reuse the callback URL.",
                "redirect_uri_mismatch": "The YouTube redirect URI does not match the URI registered for this Google OAuth client.",
                "access_denied": "Google denied access. Check the consent screen, test users, and account permissions.",
            }
            if isinstance(oauth_error, str):
                detail = messages.get(oauth_error, detail)
        elif url.startswith(f"{YOUTUBE_API_URL}/"):
            try:
                body = response.json()
            except ValueError:
                body = {}
            error = body.get("error", {}) if isinstance(body, dict) else {}
            reasons: set[str] = set()
            if isinstance(error, dict):
                for entry in error.get("errors", []) or []:
                    if isinstance(entry, dict) and isinstance(entry.get("reason"), str):
                        reasons.add(entry["reason"])
                for entry in error.get("details", []) or []:
                    if isinstance(entry, dict) and isinstance(entry.get("reason"), str):
                        reasons.add(entry["reason"])
                logger.warning(
                    "YouTube API %s failed (HTTP %d, status=%s, reasons=%s)",
                    url.rsplit("/", 1)[-1], response.status_code,
                    error.get("status"), sorted(reasons),
                )
            if reasons & {"accessNotConfigured", "SERVICE_DISABLED"}:
                detail = "YouTube Data API v3 is disabled in the Google Cloud project owning this OAuth client. Enable it in APIs & Services, then retry."
            elif reasons & {"insufficientPermissions", "ACCESS_TOKEN_SCOPE_INSUFFICIENT"}:
                detail = "The required YouTube permission was not granted. Reconnect and grant YouTube access; playlist writes require youtube.force-ssl (or youtube), not youtube.readonly. Refreshing cannot add permissions."
            elif reasons & {"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded", "RATE_LIMIT_EXCEEDED"}:
                detail = "The Google Cloud project's YouTube API quota or rate limit was exceeded. Retry after the limit resets or review the project's quota."
            elif reasons & {"youtubeSignupRequired", "channelNotFound"}:
                detail = "No usable YouTube channel was found for this account. Open YouTube, create or select a channel, then reconnect."
            elif response.status_code == 401:
                detail = "Your Google access token expired or was revoked. Refresh access or reconnect YouTube."
        raise HTTPException(
            response.status_code if response.status_code < 500 else 502,
            detail, headers=headers,
        )
    if response.status_code == 204:
        return {}
    try:
        payload = response.json()
    except ValueError as exc:
        raise HTTPException(502, "Google/YouTube returned invalid JSON.") from exc
    if not isinstance(payload, dict):
        raise HTTPException(502, "Google/YouTube returned an invalid response.")
    return payload


async def get_tokens(request: TokenRequest, code_verifier: str | None = None) -> dict[str, Any]:
    client_id, client_secret, redirect_uri = oauth_config()
    data = {"client_id": client_id, "client_secret": client_secret,
            "grant_type": request.grant_type}
    if request.grant_type == "authorization_code":
        if not code_verifier:
            raise HTTPException(400, "Missing OAuth verifier. Start YouTube login again.")
        data.update(code=request.code or "", redirect_uri=redirect_uri, code_verifier=code_verifier)
    else:
        data["refresh_token"] = request.refresh_token or ""
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        payload = await _request_json(client, "POST", GOOGLE_TOKEN_URL, data=data)
    if not isinstance(payload.get("access_token"), str) or not payload["access_token"]:
        raise HTTPException(502, "Google did not return an access token.")
    # Do not forward ID tokens or unexpected upstream fields as application identity.
    tokens = {key: payload[key] for key in
              ("access_token", "refresh_token", "token_type", "expires_in", "scope") if key in payload}
    if request.grant_type == "refresh_token" and not tokens.get("refresh_token"):
        tokens["refresh_token"] = request.refresh_token
    return tokens


async def get_user(access_token: str) -> dict[str, Any]:
    """Google account profile, not the user's YouTube channel."""
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        return await _request_json(client, "GET", GOOGLE_USERINFO_URL,
                                   headers={"Authorization": f"Bearer {access_token}"})


async def _get_collection(
    resource: Literal["channels", "playlists"], access_token: str,
    page_token: str | None, max_results: int,
) -> dict[str, Any]:
    params: dict[str, str | int] = {
        "part": "snippet,contentDetails" if resource == "channels" else "snippet,status,contentDetails",
        "mine": "true", "maxResults": max_results,
    }
    if page_token:
        params["pageToken"] = page_token
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        payload = await _request_json(
            client, "GET", f"{YOUTUBE_API_URL}/{resource}", params=params,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    # YouTube can omit items on a successful, explicitly empty page (for
    # example channels.list mine=true for an account without a channel).
    # Keep rejecting malformed non-empty responses rather than masking them.
    page_info = payload.get("pageInfo")
    if "items" not in payload and isinstance(page_info, dict) and page_info.get("totalResults") == 0:
        payload["items"] = []
    items = payload.get("items")
    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
        raise HTTPException(502, "YouTube returned an invalid collection.")
    # Native page tokens keep calls/quota bounded; never follow upstream URLs.
    return payload


async def get_channels(access_token: str, page_token: str | None = None,
                       max_results: int = 50) -> dict[str, Any]:
    return await _get_collection("channels", access_token, page_token, max_results)


async def get_user_playlists(access_token: str, page_token: str | None = None,
                             max_results: int = 50) -> dict[str, Any]:
    return await _get_collection("playlists", access_token, page_token, max_results)


async def search_videos(query: str, access_token: str) -> list[dict[str, Any]]:
    """One bounded search + metadata lookup per recommendation; no pagination.

    Only playable-looking music videos are candidates. YouTube search consumes
    quota, so do not automatically retry searches or fan out query variants.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        results = await _request_json(
            client, "GET", f"{YOUTUBE_API_URL}/search",
            params={"part": "snippet", "q": query, "type": "video",
                    "videoCategoryId": "10", "maxResults": 5}, headers=headers,
        )
        ids = [item.get("id", {}).get("videoId") for item in results.get("items", [])
               if isinstance(item, dict) and isinstance(item.get("id"), dict)]
        ids = [value for value in ids if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{11}", value)]
        if not ids:
            return []
        videos = await _request_json(
            client, "GET", f"{YOUTUBE_API_URL}/videos",
            params={"part": "snippet,contentDetails,status", "id": ",".join(ids)}, headers=headers,
        )
    items = videos.get("items", [])
    if not isinstance(items, list):
        raise HTTPException(502, "YouTube returned invalid video metadata.")
    playable = [item for item in items if isinstance(item, dict) and item.get("id") in ids
            and isinstance(item.get("snippet"), dict)
            and isinstance(item["snippet"].get("title"), str)
            and item.get("snippet", {}).get("liveBroadcastContent", "none") == "none"
            and item.get("status", {}).get("uploadStatus") == "processed"
            and item.get("status", {}).get("privacyStatus") == "public"]
    # videos.list need not preserve search ranking. Restore it explicitly so
    # first-best tie selection follows the original search result order.
    return sorted(playable, key=lambda item: ids.index(item["id"]))


async def create_playlist(request: CreatePlaylist, access_token: str) -> dict[str, Any]:
    body = {
        "snippet": {"title": request.name, "description": request.description},
        "status": {"privacyStatus": request.privacy_status},
    }
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        # Never automatically retry writes: a timeout may follow a successful write.
        return await _request_json(
            client, "POST", f"{YOUTUBE_API_URL}/playlists",
            params={"part": "snippet,status"}, json=body,
            headers={"Authorization": f"Bearer {access_token}"},
        )


async def update_playlist(playlist_id: str, request: UpdatePlaylist,
                          access_token: str) -> dict[str, Any]:
    # Read before writing to retain snippet fields this API does not expose.
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        headers = {"Authorization": f"Bearer {access_token}"}
        current = await _request_json(
            client, "GET", f"{YOUTUBE_API_URL}/playlists",
            params={"part": "snippet", "id": playlist_id}, headers=headers,
        )
        items = current.get("items", [])
        if not isinstance(items, list) or not items:
            raise HTTPException(404, "YouTube playlist not found or inaccessible.")
        snippet = items[0].get("snippet", {})
        preserved = {key: snippet[key] for key in ("tags", "defaultLanguage") if key in snippet}
        body: dict[str, Any] = {
            "id": playlist_id,
            "snippet": {**preserved, "title": request.name, "description": request.description},
        }
        part = "snippet"
        if request.privacy_status is not None:
            body["status"] = {"privacyStatus": request.privacy_status}
            part += ",status"
        return await _request_json(
            client, "PUT", f"{YOUTUBE_API_URL}/playlists",
            params={"part": part}, json=body, headers=headers,
        )


async def delete_playlist(playlist_id: str, access_token: str) -> None:
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        await _request_json(
            client, "DELETE", f"{YOUTUBE_API_URL}/playlists",
            params={"id": playlist_id}, headers={"Authorization": f"Bearer {access_token}"},
        )


async def add_item_to_playlist(playlist_id: str, request: AddItemRequest,
                               access_token: str) -> dict[str, Any]:
    snippet: dict[str, Any] = {
        "playlistId": playlist_id,
        "resourceId": {"kind": "youtube#video", "videoId": request.video_id},
    }
    if request.position is not None:
        snippet["position"] = request.position
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        return await _request_json(
            client, "POST", f"{YOUTUBE_API_URL}/playlistItems",
            params={"part": "snippet"}, json={"snippet": snippet},
            headers={"Authorization": f"Bearer {access_token}"},
        )


async def remove_item_from_playlist(playlist_item_id: str, access_token: str) -> None:
    # This is the playlist-item ID returned by insertion, NOT the video ID.
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        await _request_json(
            client, "DELETE", f"{YOUTUBE_API_URL}/playlistItems",
            params={"id": playlist_item_id}, headers={"Authorization": f"Bearer {access_token}"},
        )