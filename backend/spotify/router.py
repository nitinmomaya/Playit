

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from login.service import STATE_COOKIE, validate_oauth_state
from spotify.web_api import TokenRequest, get_tokens, get_user, get_user_playlists, create_playlist

router = APIRouter(prefix="/spotify", tags=["Spotify"])

from models.song_details_model.songsdetails import  SongRecommendations

from spotify.service import recommend_songs, RecommendationRequest

from spotify.web_api import CreatePlaylist,AddItemRequest, RemoveItemRequest, UpdateItemRequest, add_item_to_playlist, remove_item_from_playlist, update_item_from_playlist

bearer = HTTPBearer(auto_error=False)


def access_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> str:
    if not credentials:
        raise HTTPException(status_code=401, detail="A bearer access token is required.",
                            headers={"WWW-Authenticate": "Bearer"})
    return credentials.credentials


@router.post("/token")
async def token(body: TokenRequest, request: Request, response: Response) -> dict[str, Any]:
    if body.grant_type == "authorization_code":
        validate_oauth_state(request, body.state)
    tokens = await get_tokens(body)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    if body.grant_type == "authorization_code":
        response.delete_cookie(STATE_COOKIE, path="/")
    return tokens


@router.get("/me")
async def me(token: Annotated[str, Depends(access_token)]) -> dict[str, Any]:
    return await get_user(token)


@router.get("/users/{user_id}/playlists")

async def playlists(user_id: str, token: Annotated[str, Depends(access_token)]) -> dict[str, Any]:
    """Get a user's playlists."""
    return await get_user_playlists(user_id, token)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "spotify"}


@router.post("/recommendations", response_model=SongRecommendations)
def get_recommendations(request: RecommendationRequest) -> SongRecommendations:
    try:
        return recommend_songs(request)
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not get recommendations: {exc}",
        ) from exc

@router.post("/users/{user_id}/create_playlist")
async def create_playlist(user_id: str, request: CreatePlaylist) :
    """Create a new playlist based on the recommendation request."""
    try:
        #create playlist based on the songs recommeneded in spotify
        return await create_playlist(user_id, request)
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not create playlist: {exc}",
        ) from exc

@router.post("/add_item/{playlist_id}/items")
async def add_item(playlist_id: str, request: AddItemRequest):
    """Add an item to a playlist."""
    try:
        return await add_item_to_playlist(playlist_id, request)
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not add item to playlist: {exc}",
        ) from exc

@router.post("/remove_item/{playlist_id}/items")
async def remove_item(playlist_id: str, request: RemoveItemRequest):
    """Remove an item from a playlist."""
    try:
        return await remove_item_from_playlist(playlist_id, request)
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not remove item from playlist: {exc}",
        ) from exc

@router.put("/update_item/{playlist_id}/items")
async def update_item(playlist_id: str, request: UpdateItemRequest):
    """Update an item in a playlist."""
    try:
        return await update_item_from_playlist(playlist_id, request)
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not update item in playlist: {exc}",
        ) from exc

    