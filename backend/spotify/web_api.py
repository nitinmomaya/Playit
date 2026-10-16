"""Server-side Spotify OAuth and Web API requests."""

import os
import ssl
from typing import Any, Literal
from urllib.parse import quote

import httpx
import truststore
from dotenv import load_dotenv
from fastapi import HTTPException
from pydantic import BaseModel, Field, model_validator

load_dotenv()

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_URL = "https://api.spotify.com/v1"


def _ssl_context() -> ssl.SSLContext:
    # Trust OS-managed certificates without disabling TLS verification.
    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ca_file = os.getenv("SSL_CERT_FILE")
    ca_dir = os.getenv("SSL_CERT_DIR")
    if ca_file or ca_dir:
        context.load_verify_locations(cafile=ca_file, capath=ca_dir)
    return context


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
    name: str = Field(..., min_length=1)
    description: str = Field(default="", max_length=300)
    public: bool = False


class AddItemRequest(BaseModel):
    uris: list[str] = Field(..., min_length=1, max_length=100)
    position: int | None = Field(default=None, ge=0)

class UpdateItemRequest(BaseModel):
    range_start: int | None = Field(default=None, ge=0)
    insert_before: int | None = Field(default=None, ge=0)
    range_length: int | None = Field(default=None, ge=0)

class RemoveItemRequest(BaseModel):
    uris: list[str] = Field(..., min_items=1)
    snapshot_id: str | None = Field(default=None, min_length=1)

async def _request_json(
    client: httpx.AsyncClient, method: str, url: str, **kwargs: Any
) -> dict[str, Any]:
    try:
        response = await client.request(method, url, **kwargs)
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Spotify request timed out.") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Could not connect to Spotify.") from exc

    if response.is_error:
        headers = {}
        if response.status_code == 429 and "Retry-After" in response.headers:
            headers["Retry-After"] = response.headers["Retry-After"]
        raise HTTPException(
            status_code=response.status_code if response.status_code < 500 else 502,
            detail="Spotify rejected the request. Check the token, permissions, or request parameters.",
            headers=headers,
        )
    try:
        payload = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Spotify returned invalid JSON.") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=502, detail="Spotify returned an invalid response.")
    return payload


async def get_tokens(request: TokenRequest) -> dict[str, Any]:
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(status_code=503, detail="Spotify OAuth is not configured.")

    data = {"grant_type": request.grant_type}
    if request.grant_type == "authorization_code":
        redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")
        if not redirect_uri:
            raise HTTPException(status_code=503, detail="Spotify redirect URI is not configured.")
        data.update(code=request.code or "", redirect_uri=redirect_uri)
    else:
        data["refresh_token"] = request.refresh_token or ""

    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        payload = await _request_json(
            client, "POST", SPOTIFY_TOKEN_URL, data=data, auth=(client_id, client_secret)
        )
    if not payload.get("access_token"):
        raise HTTPException(status_code=502, detail="Spotify did not return an access token.")
    # Spotify may omit refresh_token during refresh; keep the existing token.
    if request.grant_type == "refresh_token" and not payload.get("refresh_token"):
        payload["refresh_token"] = request.refresh_token
    return payload


async def get_user(access_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        return await _request_json(
            client, "GET", f"{SPOTIFY_API_URL}/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )


async def get_user_playlists(user_id: str, access_token: str) -> dict[str, Any]:
    """Collect every page without following upstream URLs with bearer credentials."""
    items: list[dict[str, Any]] = []
    offset = 0
    url = f"{SPOTIFY_API_URL}/users/{quote(user_id, safe='')}/playlists"
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        while True:
            page = await _request_json(
                client, "GET", url,
                headers={"Authorization": f"Bearer {access_token}"},
                params={"limit": 50, "offset": offset},
            )
            page_items = page.get("items")
            if not isinstance(page_items, list):
                raise HTTPException(status_code=502, detail="Spotify returned invalid playlists.")
            items.extend(page_items)
            if not page.get("next"):
                break
            if not page_items or offset + len(page_items) > 100_000:
                raise HTTPException(status_code=502, detail="Spotify returned invalid pagination.")
            offset += len(page_items)
    return {"items": items, "total": len(items)}

async def create_playlist(user_id: str, request: CreatePlaylist, access_token: str) -> dict[str, Any]:
    """Create Playlist for User"""
    #validate request parameters
    if request.name is None or request.description is None or request.public is None:
        raise HTTPException(status_code=400, detail="Invalid request parameters.")
    body={
        "name": request.name,
        "description": request.description,
        "public": request.public,
    }
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        return await _request_json(
            client, "POST", f"{SPOTIFY_API_URL}/me/playlists",
            headers={"Authorization": f"Bearer {access_token}"},
            json=body,
        )


async def add_item_to_playlist(
    playlist_id: str, request: AddItemRequest, access_token: str
) -> dict[str, Any]:
    """Add an item to a playlist."""

    body = request.model_dump(exclude_none=True)
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        return await _request_json(
            client, "POST", f"{SPOTIFY_API_URL}/playlists/{quote(playlist_id, safe='')}/items",
            headers={"Authorization": f"Bearer {access_token}"},
            json=body,
        )


async def search_tracks(query: str, access_token: str) -> list[dict[str, Any]]:
    """Search with the user's account market; never accept upstream URLs."""
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        payload = await _request_json(
            client, "GET", f"{SPOTIFY_API_URL}/search",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"q": query, "type": "track", "limit": 10},
        )
    tracks = payload.get("tracks")
    items = tracks.get("items") if isinstance(tracks, dict) else None
    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
        raise HTTPException(status_code=502, detail="Spotify returned invalid search results.")
    return items

async def remove_item_from_playlist(playlist_id: str, request: RemoveItemRequest) -> dict[str, Any]:
    """Remove an item from a playlist."""

    #validate request parameters
    if not request.uris:
        raise HTTPException(status_code=400, detail="Invalid request parameters.")
    body ={
        "uris": request.uris,
    }
    if request.snapshot_id is not None:
        body["snapshot_id"] = request.snapshot_id
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        return await _request_json(
            client, "DELETE", f"{SPOTIFY_API_URL}/playlists/{quote(playlist_id, safe='')}/items",
            headers={"Authorization": f"Bearer {request.access_token}"},
            json=body,
        )

async def update_item_from_playlist(playlist_id: str, request: UpdateItemRequest) -> dict[str, Any]:
    """Update an item in a playlist."""

    #validate request parameters
    if request.range_start is None or request.range_before is None or request.range_length is None:
        raise HTTPException(status_code=400, detail="Invalid request parameters.")
    body ={
        "range_start": request.range_start,
        "range_before": request.range_before,
        "range_length": request.range_length,
    }
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        return await _request_json(
            client, "PUT", f"{SPOTIFY_API_URL}/playlists/{quote(playlist_id, safe='')}/items",
            headers={"Authorization": f"Bearer {request.access_token}"},
            json=body,
        )
    