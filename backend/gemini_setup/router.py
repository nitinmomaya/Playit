from fastapi import APIRouter, HTTPException
from fastapi import Depends
from fastapi.responses import StreamingResponse
import httpx
from google.genai.errors import APIError
from typing import Annotated, Literal
from gemini_setup.conversation import ConversationRequest
from gemini_setup.agent import run_agent
from spotify.router import access_token

from gemini_setup.service import (
    GeminiConfigurationError,
    GeminiRequestError,
    classify_request,
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
    """Route the request and execute playlist preparation before reporting success."""
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
    return {"action": classify_request(request)}


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