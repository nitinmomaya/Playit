

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/spotify", tags=["Spotify"])

from models.song_details_model.songsdetails import  SongRecommendations

from spotify.service import recommend_songs, RecommendationRequest


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
