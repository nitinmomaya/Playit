"""Bounded Gemini tool-calling agent for Playit's playlist workflow."""

import os
import json
from typing import Any

from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool
from google import genai
from google.genai import types

from gemini_setup.conversation import ConversationRequest
from models.song_details_model.songsdetails import SongRecommendations
from music.models import PlaylistProposal
from music.service import playlist_service
from spotify.service import RecommendationRequest, recommend_songs

MAX_AGENT_TURNS = 4

_PLAYLIST_TOOL = types.FunctionDeclaration(
    name="prepare_playlist",
    description=(
        "Prepare a playlist draft when the user explicitly asks for a playlist, "
        "song recommendations, or a refinement of a prior playlist request. "
        "This only prepares a reviewable draft; it never approves or creates a Spotify playlist."
    ),
    parameters_json_schema={"type": "object", "properties": {}, "additionalProperties": False},
)

_SYSTEM_INSTRUCTION = (
    "You are Playit, a music assistant. Respond naturally to ordinary music questions. "
    "For a clear request to recommend songs or build/refine a playlist, call prepare_playlist. "
    "Do not call it for greetings, general music questions, or mere discussion of playlists. "
    "The tool only prepares a draft. Never claim a playlist was created: the user must review "
    "and approve it in Playit. Do not ask for or expose credentials."
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


async def _prepare_playlist(request: ConversationRequest, spotify_token: str) -> tuple[str, str]:
    """Use existing recommendation and draft services; this does not write to Spotify."""
    recommendations: SongRecommendations = await run_in_threadpool(
        recommend_songs,
        RecommendationRequest(prompt=request.prompt, history=request.history),
    )
    proposal = PlaylistProposal.model_validate({
        "name": recommendations.name,
        "description": recommendations.description,
        "public": False,
        "songs": [
            {"songname": song.songname, "artistname": song.artistname}
            for song in recommendations.recommendations
        ],
        "requested_count": recommendations.requested_count,
        "target_duration_ms": recommendations.target_duration_ms,
    })
    preview = await playlist_service.prepare(proposal, spotify_token)
    context_text = json.dumps({
        "message": recommendations.message,
        "name": recommendations.name,
        "description": recommendations.description,
        "recommendations": [
            {"songname": song.songname, "artistname": song.artistname}
            for song in recommendations.recommendations
        ],
    }, ensure_ascii=False)
    return preview.draft_id, context_text


async def run_agent(request: ConversationRequest, spotify_token: str) -> dict[str, str | None]:
    """Let Gemini select the safe preparation tool; keep approval in the Playit UI."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="Gemini API key is missing.")

    model = os.getenv("GEMINI_PRIMARY_MODEL", "gemini-3.5-flash-lite")
    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=60_000))
    config = types.GenerateContentConfig(
        system_instruction=_SYSTEM_INSTRUCTION,
        tools=[types.Tool(function_declarations=[_PLAYLIST_TOOL])],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        max_output_tokens=1024,
    )
    contents = _conversation_contents(request)
    draft_id: str | None = None
    context_text: str | None = None

    async with client.aio as async_client:
        for _ in range(MAX_AGENT_TURNS):
            response = await async_client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
            calls = response.function_calls or []
            if not calls:
                text = (response.text or "").strip()
                if not text and draft_id:
                    text = "Your playlist draft is ready to review below."
                if not text:
                    text = "I couldn't produce a response. Please try again."
                return {"text": text, "draft_id": draft_id, "context_text": context_text}

            candidate = response.candidates[0] if response.candidates else None
            if candidate and candidate.content:
                contents.append(candidate.content)

            function_responses: list[types.Part] = []
            for call in calls:
                result: dict[str, Any]
                if call.name != "prepare_playlist":
                    result = {"error": "This tool is not available."}
                elif draft_id is not None:
                    result = {"error": "A draft has already been prepared for this request."}
                else:
                    try:
                        draft_id, context_text = await _prepare_playlist(request, spotify_token)
                        result = {"status": "awaiting_user_review", "draft_id": draft_id}
                    except HTTPException as exc:
                        result = {"error": str(exc.detail)}
                function_responses.append(
                    types.Part.from_function_response(name=call.name or "unknown", response=result)
                )
            contents.append(types.Content(role="user", parts=function_responses))

    return {
        "text": "Your playlist draft is ready to review below." if draft_id else "I couldn't complete that request. Please try again.",
        "draft_id": draft_id,
        "context_text": context_text,
    }