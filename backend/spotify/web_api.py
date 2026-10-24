"""Server-side Spotify OAuth and Web API requests."""

# Import os.
import os
# Import ssl.
import ssl
# Import Any, Literal.
from typing import Any, Literal
# Import quote.
from urllib.parse import quote

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

# Set SPOTIFY_TOKEN_URL.
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
# Set SPOTIFY_API_URL.
SPOTIFY_API_URL = "https://api.spotify.com/v1"


# Define _ssl_context.
def _ssl_context() -> ssl.SSLContext:
    # Trust OS-managed certificates without disabling TLS verification.
    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    # Read ca_file from server configuration.
    ca_file = os.getenv("SSL_CERT_FILE")
    # Read ca_dir from server configuration.
    ca_dir = os.getenv("SSL_CERT_DIR")
    # Check ca_file or ca_dir.
    if ca_file or ca_dir:
        # Call context.load_verify_locations.
        context.load_verify_locations(cafile=ca_file, capath=ca_dir)
    # Return context.
    return context


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

# Group the fields/behavior of CreatePlaylist.
class CreatePlaylist(BaseModel):
    # Validate/configure name.
    name: str = Field(..., min_length=1)
    # Validate/configure description.
    description: str = Field(default="", max_length=300)
    # Declare public.
    public: bool = False


# Group the fields/behavior of AddItemRequest.
class AddItemRequest(BaseModel):
    # Validate/configure uris.
    uris: list[str] = Field(..., min_length=1, max_length=100)
    # Validate/configure position.
    position: int | None = Field(default=None, ge=0)

# Group the fields/behavior of UpdateItemRequest.
class UpdateItemRequest(BaseModel):
    # Validate/configure range_start.
    range_start: int | None = Field(default=None, ge=0)
    # Validate/configure insert_before.
    insert_before: int | None = Field(default=None, ge=0)
    # Validate/configure range_length.
    range_length: int | None = Field(default=None, ge=0)

# Group the fields/behavior of RemoveItemRequest.
class RemoveItemRequest(BaseModel):
    # Validate/configure uris.
    uris: list[str] = Field(..., min_items=1)
    # Validate/configure snapshot_id.
    snapshot_id: str | None = Field(default=None, min_length=1)

# Define _request_json as an awaited operation.
async def _request_json(
    client: httpx.AsyncClient, method: str, url: str, **kwargs: Any
) -> dict[str, Any]:
    # Handle failures from this operation below.
    try:
        # Wait for the operation and keep response.
        response = await client.request(method, url, **kwargs)
    except httpx.TimeoutException as exc:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(status_code=504, detail="Spotify request timed out.") from exc
    except httpx.RequestError as exc:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(status_code=502, detail="Could not connect to Spotify.") from exc

    # Check response.is_error.
    if response.is_error:
        # Set headers.
        headers = {}
        # Check response.status_code == 429 and 'Retry-After' in response.headers.
        if response.status_code == 429 and "Retry-After" in response.headers:
            # Set headers['Retry-After'].
            headers["Retry-After"] = response.headers["Retry-After"]
        # Stop this request with an explicit HTTP error.
        raise HTTPException(
            status_code=response.status_code if response.status_code < 500 else 502,
            detail="Spotify rejected the request. Check the token, permissions, or request parameters.",
            headers=headers,
        )
    # Handle failures from this operation below.
    try:
        # Set payload.
        payload = response.json()
    except ValueError as exc:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(status_code=502, detail="Spotify returned invalid JSON.") from exc
    # Check not isinstance(payload, dict).
    if not isinstance(payload, dict):
        # Stop this request with an explicit HTTP error.
        raise HTTPException(status_code=502, detail="Spotify returned an invalid response.")
    # Return payload.
    return payload


# Define get_tokens as an awaited operation.
async def get_tokens(request: TokenRequest) -> dict[str, Any]:
    # Read client_id from server configuration.
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    # Read client_secret from server configuration.
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    # Check not client_id or not client_secret.
    if not client_id or not client_secret:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(status_code=503, detail="Spotify OAuth is not configured.")

    # Set data.
    data = {"grant_type": request.grant_type}
    # Check request.grant_type == 'authorization_code'.
    if request.grant_type == "authorization_code":
        # Read redirect_uri from server configuration.
        redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")
        # Check not redirect_uri.
        if not redirect_uri:
            # Stop this request with an explicit HTTP error.
            raise HTTPException(status_code=503, detail="Spotify redirect URI is not configured.")
        # Call data.update.
        data.update(code=request.code or "", redirect_uri=redirect_uri)
    else:
        # Set data['refresh_token'].
        data["refresh_token"] = request.refresh_token or ""

    # Manage httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) with automatic cleanup.
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        # Wait for the operation and keep payload.
        payload = await _request_json(
            client, "POST", SPOTIFY_TOKEN_URL, data=data, auth=(client_id, client_secret)
        )
    # Check not payload.get('access_token').
    if not payload.get("access_token"):
        # Stop this request with an explicit HTTP error.
        raise HTTPException(status_code=502, detail="Spotify did not return an access token.")
    # Spotify may omit refresh_token during refresh; keep the existing token.
    if request.grant_type == "refresh_token" and not payload.get("refresh_token"):
        # Set payload['refresh_token'].
        payload["refresh_token"] = request.refresh_token
    # Return payload.
    return payload


# Define get_user as an awaited operation.
async def get_user(access_token: str) -> dict[str, Any]:
    # Manage httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) with automatic cleanup.
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        # Return await _request_json(client, 'GET', f'{SPOTIFY_API_URL}/me', headers={'Autho....
        return await _request_json(
            client, "GET", f"{SPOTIFY_API_URL}/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )


async def get_user_playlists(user_id: str, access_token: str) -> dict[str, Any]:
    """Collect every page without following upstream URLs with bearer credentials."""
    # Declare items.
    items: list[dict[str, Any]] = []
    # Set offset.
    offset = 0
    # Set url.
    url = f"{SPOTIFY_API_URL}/users/{quote(user_id, safe='')}/playlists"
    # Manage httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) with automatic cleanup.
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        # Repeat while True.
        while True:
            # Wait for the operation and keep page.
            page = await _request_json(
                client, "GET", url,
                headers={"Authorization": f"Bearer {access_token}"},
                params={"limit": 50, "offset": offset},
            )
            # Set page_items.
            page_items = page.get("items")
            # Check not isinstance(page_items, list).
            if not isinstance(page_items, list):
                # Stop this request with an explicit HTTP error.
                raise HTTPException(status_code=502, detail="Spotify returned invalid playlists.")
            # Call items.extend.
            items.extend(page_items)
            # Check not page.get('next').
            if not page.get("next"):
                break
            # Check not page_items or offset + len(page_items) > 100000.
            if not page_items or offset + len(page_items) > 100_000:
                # Stop this request with an explicit HTTP error.
                raise HTTPException(status_code=502, detail="Spotify returned invalid pagination.")
            # Update offset.
            offset += len(page_items)
    # Return the assembled result to the caller.
    return {"items": items, "total": len(items)}

async def create_playlist(user_id: str, request: CreatePlaylist, access_token: str) -> dict[str, Any]:
    """Create Playlist for User"""
    #validate request parameters
    if request.name is None or request.description is None or request.public is None:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(status_code=400, detail="Invalid request parameters.")
    # Set body.
    body={
        "name": request.name,
        "description": request.description,
        "public": request.public,
    }
    # Manage httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) with automatic cleanup.
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        # Return await _request_json(client, 'POST', f'{SPOTIFY_API_URL}/me/playlists', head....
        return await _request_json(
            client, "POST", f"{SPOTIFY_API_URL}/me/playlists",
            headers={"Authorization": f"Bearer {access_token}"},
            json=body,
        )


async def add_item_to_playlist(
    playlist_id: str, request: AddItemRequest, access_token: str
) -> dict[str, Any]:
    """Add an item to a playlist."""

    # Set body.
    body = request.model_dump(exclude_none=True)
    # Manage httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) with automatic cleanup.
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        # Return await _request_json(client, 'POST', f"{SPOTIFY_API_URL}/playlists/{quote(pl....
        return await _request_json(
            client, "POST", f"{SPOTIFY_API_URL}/playlists/{quote(playlist_id, safe='')}/items",
            headers={"Authorization": f"Bearer {access_token}"},
            json=body,
        )


async def search_tracks(query: str, access_token: str) -> list[dict[str, Any]]:
    """Search with the user's account market; never accept upstream URLs."""
    # Manage httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) with automatic cleanup.
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        # Wait for the operation and keep payload.
        payload = await _request_json(
            client, "GET", f"{SPOTIFY_API_URL}/search",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"q": query, "type": "track", "limit": 10},
        )
    # Set tracks.
    tracks = payload.get("tracks")
    # Set items.
    items = tracks.get("items") if isinstance(tracks, dict) else None
    # Check not isinstance(items, list) or any((not isinstance(item, dict) for item in ....
    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
        # Stop this request with an explicit HTTP error.
        raise HTTPException(status_code=502, detail="Spotify returned invalid search results.")
    # Return items.
    return items

async def remove_item_from_playlist(playlist_id: str, request: RemoveItemRequest) -> dict[str, Any]:
    """Remove an item from a playlist."""

    #validate request parameters
    if not request.uris:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(status_code=400, detail="Invalid request parameters.")
    # Set body.
    body ={
        "uris": request.uris,
    }
    # Check request.snapshot_id is not None.
    if request.snapshot_id is not None:
        # Set body['snapshot_id'].
        body["snapshot_id"] = request.snapshot_id
    # Manage httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) with automatic cleanup.
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        # Return await _request_json(client, 'DELETE', f"{SPOTIFY_API_URL}/playlists/{quote(....
        return await _request_json(
            client, "DELETE", f"{SPOTIFY_API_URL}/playlists/{quote(playlist_id, safe='')}/items",
            headers={"Authorization": f"Bearer {request.access_token}"},
            json=body,
        )

async def update_item_from_playlist(playlist_id: str, request: UpdateItemRequest) -> dict[str, Any]:
    """Update an item in a playlist."""

    #validate request parameters
    if request.range_start is None or request.range_before is None or request.range_length is None:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(status_code=400, detail="Invalid request parameters.")
    # Set body.
    body ={
        "range_start": request.range_start,
        "range_before": request.range_before,
        "range_length": request.range_length,
    }
    # Manage httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) with automatic cleanup.
    async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
        # Return await _request_json(client, 'PUT', f"{SPOTIFY_API_URL}/playlists/{quote(pla....
        return await _request_json(
            client, "PUT", f"{SPOTIFY_API_URL}/playlists/{quote(playlist_id, safe='')}/items",
            headers={"Authorization": f"Bearer {request.access_token}"},
            json=body,
        )

# File summary
# - Makes verified-TLS Spotify OAuth and Web API calls.
# - Validates upstream JSON and maps network/provider failures.
# - Provides search/create/add plus older incomplete remove/update helpers.
