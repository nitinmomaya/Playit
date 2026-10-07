
import json
from gemini_setup.service import (
    GeminiConfigurationError,
    GeminiRequestError,
    create_interaction,
)
from fastapi import  HTTPException
import httpx
from google.genai.errors import APIError
from pydantic import BaseModel


from models.song_details_model.songsdetails import  SongRecommendations


class RecommendationRequest(BaseModel):
    prompt: str

def recommend_songs(request: RecommendationRequest) -> SongRecommendations:
    prompt = (
        "Recommend 5 songs that match this request for a Spotify playlist. "
        "Respond only with valid JSON in this exact structure: "
        '{"message":"A friendly one-sentence response to the user",'
        '"recommendations":[{"songname":"...","artistname":"...",'
        '"genre":"...","language":"...","mood":"...",'
        '"release_date":"YYYY-MM-DD or YYYY"}]}. '
        "Return actual song and artist names; do not return blank strings or "
        "the example placeholder values. If metadata is uncertain, use "
        "'Unknown' instead of leaving the field blank. Do not include "
        "markdown fences or text outside the JSON.\n\n"
        f"Request: {request.prompt}"
    )
    try:
        output = create_interaction(prompt)
        try:
            parsed_output = json.loads(output)
            return SongRecommendations.model_validate(parsed_output)
        except (json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(
                status_code=502,
                detail="Gemini returned song recommendations in an invalid format.",
            ) from exc
    except GeminiConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="Gemini did not respond before the request timed out.",
        ) from exc
    except GeminiRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except APIError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini request failed: {exc.message}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not get recommendations from Gemini: {exc}",
        ) from exc