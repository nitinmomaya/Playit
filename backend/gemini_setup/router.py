from fastapi import APIRouter, HTTPException
from fastapi import Depends
from fastapi.responses import StreamingResponse
import httpx
from google.genai.errors import APIError
import json
from typing import Annotated, Literal
from gemini_setup.conversation import ConversationRequest
from gemini_setup.agent import run_agent
from spotify.router import access_token

from gemini_setup.service import (
    GeminiConfigurationError,
    GeminiRequestError,
    create_interaction,
    create_stream_response,
)

router = APIRouter(prefix="/gemini", tags=["Gemini"])


InteractionRequest = ConversationRequest


@router.post("/agent")
async def run_agent_interaction(
    request: InteractionRequest,
    token: Annotated[str, Depends(access_token)],
    provider: Literal["spotify", "youtube"] = "spotify",
) -> dict[str, str | None]:
    """Run Gemini's bounded tool-calling workflow for the authenticated user."""
    try:
        return await run_agent(request, token, provider)
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Gemini did not respond before the request timed out.") from exc
    except APIError as exc:
        raise HTTPException(status_code=502, detail="Gemini could not complete the agent request.") from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Could not complete the agent request.") from exc


@router.post("/intent")
def classify_intent(request: InteractionRequest) -> dict[str, str]:
    """Plan a conversational action; never authorize a Spotify write."""
    instruction = (
        "Classify the current music conversation request. Return ONLY JSON "
        '{"action":"playlist"} or {"action":"chat"}. '
        "Use playlist for requests to recommend/find songs, make/build a playlist or mix, "
        "or refine an earlier recommendation (such as 'more upbeat', 'only Hindi', "
        "'make that a playlist', 'add more songs like those', 'I asked for 10', "
        "'make it 2 hours', 'you only gave me 3 songs'). Use chat for greetings, "
        "music questions/explanations, questions about a playlist, cancellations, or unrelated conversation. "
        "A mention of Spotify or the word playlist alone is not enough. "
        "Do not interpret approval/confirmation as permission to write; approval happens in the UI. "
        f"Current user message: {request.prompt}"
    )
    try:
        result = json.loads(create_interaction(instruction, request.history))
        if not isinstance(result, dict) or result.get("action") not in ("playlist", "chat"):
            raise ValueError("Invalid intent response")
        return {"action": result["action"]}
    except GeminiConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Could not understand the request. Please try again.") from exc


@router.post("/interactions/stream")
async def run_stream(request: InteractionRequest) -> StreamingResponse:
    return create_stream_response(request.prompt, request.history)


@router.post("/interactions")
def run_interaction(request: InteractionRequest) -> dict[str, str]:
    try:
        return {"output": create_interaction(request.prompt, request.history)}
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
            detail="Could not get a response from Gemini.",
        ) from exc