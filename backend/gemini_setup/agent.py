"""Route Gemini's intent to an executed playlist workflow or a chat reply."""

import os
from typing import Literal

from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool
from google import genai
from google.genai import types

from gemini_setup.conversation import ConversationRequest
from gemini_setup.service import classify_request
from recommendations.langgraph_workflow import prepare_recommendations, recommendation_context

_SYSTEM_INSTRUCTION = (
    "You are Playit, a music assistant. Respond naturally to ordinary music questions. "
    "This call is for conversation only and has not prepared or created any playlist. "
    "Never claim a draft is ready or that a review panel exists based on conversation text. "
    "Actual playlist drafts appear below the response that prepared them, with an approval button. "
    "If that preview is missing, ask the user to resend their playlist request to generate a new draft. "
    "Approval happens only through the visible preview button, not chat confirmation. "
    "Do not ask for or expose credentials."
)


def _conversation_contents(request: ConversationRequest) -> list[types.Content]:
    contents = [
        types.Content(
            role="model" if turn.role == "assistant" else "user",
            parts=[types.Part.from_text(text=turn.text)],
        )
        for turn in request.history
    ]
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=request.prompt)]))
    return contents


async def _prepare_playlist(request: ConversationRequest, spotify_token: str,
                            provider: Literal["spotify", "youtube"] = "spotify") -> tuple[str, str]:
    """Use existing recommendation and draft services; this does not write to Spotify."""
    preview, recommendations = await prepare_recommendations(request, spotify_token, provider)
    return preview.draft_id, recommendation_context(recommendations)


async def run_agent(request: ConversationRequest, spotify_token: str,
                    provider: Literal["spotify", "youtube"] = "spotify") -> dict[str, str | None]:
    """Report a draft only after successful preparation; propagate workflow errors."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="Gemini API key is missing.")

    action = await run_in_threadpool(classify_request, request)
    if action == "playlist":
        draft_id, context_text = await _prepare_playlist(request, spotify_token, provider)
        return {
            "text": "Review the matched songs below, then use the approval button to create your playlist.",
            "draft_id": draft_id,
            "context_text": context_text,
        }

    model = os.getenv("GEMINI_PRIMARY_MODEL", "gemini-3.5-flash-lite")
    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=60_000))
    config = types.GenerateContentConfig(
        system_instruction=_SYSTEM_INSTRUCTION + f" The selected destination is {provider}. Do not change it.",
        max_output_tokens=1024,
    )
    async with client.aio as async_client:
        response = await async_client.models.generate_content(
            model=model, contents=_conversation_contents(request), config=config,
        )
    return {
        "text": (response.text or "").strip() or "I couldn't produce a response. Please try again.",
        "draft_id": None,
        "context_text": None,
    }