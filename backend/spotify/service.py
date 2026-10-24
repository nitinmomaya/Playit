
import json
import math
from music.constraints import requested_quantity
from gemini_setup.service import (
    GeminiConfigurationError,
    GeminiRequestError,
    create_interaction,
)
from fastapi import  HTTPException
import httpx
from google.genai.errors import APIError
from gemini_setup.conversation import ConversationRequest, contextual_prompt


from models.song_details_model.songsdetails import  SongRecommendations


RecommendationRequest = ConversationRequest

def recommend_songs(request: RecommendationRequest) -> SongRecommendations:
    count, duration = requested_quantity(request)
    candidate_count = count or (min(200, math.ceil(duration / 150_000) + 5) if duration else 5)
    prompt = (
        f"Recommend exactly {candidate_count} distinct songs that match this request for a music playlist. "
        "Return the complete requested list, not a sample or only additional songs. "
        + (f"The target listening time is {duration / 60_000:g} minutes. These are candidates; "
           "the server will select whole tracks using verified Spotify durations. " if duration else "") +
        "Respond only with valid JSON in this exact structure: "
        '{"message":"A friendly one-sentence response to the user",'
        '"name":"A short creative playlist title based on the request",'
        '"description":"A concise description of the playlist mood, era and style",'
        '"recommendations":[{"songname":"...","artistname":"...",'
        '"genre":"...","language":"...","mood":"...",'
        '"release_date":"YYYY-MM-DD or YYYY"}]}. '
        "Generate the playlist name and description from the request, not generic placeholders. "
        "The name must end with '-Playit' (example: 2000's Best Songs-Playit). "
        "The description must end with 'created via Playit'. "
        "Return actual song and artist names; do not return blank strings or "
        "the example placeholder values. If metadata is uncertain, use "
        "'Unknown' instead of leaving the field blank. Do not include "
        "markdown fences or text outside the JSON.\n\n"
        f"Request: {request.prompt}"
    )
    try:
        for attempt in range(3):
            output = create_interaction(contextual_prompt(prompt, request.history))
            try:
                result = SongRecommendations.model_validate(json.loads(output))
            except (json.JSONDecodeError, ValueError):
                if attempt == 2:
                    raise HTTPException(502, "Gemini returned invalid recommendations after three attempts.")
                continue
            unique = list({(song.songname.strip().casefold(), song.artistname.strip().casefold()): song
                           for song in result.recommendations}.values())
            if (count is not None or duration is not None) and len(unique) < candidate_count:
                prompt += (f"\nYour previous response contained only {len(unique)} unique songs. "
                           f"Return a complete replacement list of exactly {candidate_count} unique songs.")
                if attempt < 2:
                    continue
                raise HTTPException(502, f"Gemini returned only {len(unique)} of {candidate_count} required songs. Please retry; no shorter playlist was accepted.")
            result.recommendations = unique[:candidate_count]
            result.requested_count, result.target_duration_ms = count, duration
            return result
        raise HTTPException(502, "Could not generate a complete playlist.")
    except HTTPException:
        raise
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

