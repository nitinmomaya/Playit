"""LangGraph owns bounded generate, resolve, assess, and draft transitions."""

import asyncio
import json
import math
from typing import Literal, TypedDict

from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool
from langgraph.graph import END, START, StateGraph
from langsmith import tracing_context

from gemini_setup.conversation import ConversationRequest
from models.song_details_model.songsdetails import SongRecommendations
from music.constraints import requested_quantity
from music.models import PlaylistPreview, PlaylistProposal, SongMatch
from music.service import PlaylistService, playlist_service
from recommendations.langchain_model import generate_candidates

MAX_GENERATION_ROUNDS = 3
MAX_CANDIDATES = 200
WORKFLOW_TIMEOUT_SECONDS = 120


def recommendation_context(recommendations: SongRecommendations) -> str:
    """Only independently generated suggestions may enter future model history."""
    return json.dumps({
        "message": recommendations.message,
        "name": recommendations.name,
        "description": recommendations.description,
        "recommendations": [
            {"songname": song.songname, "artistname": song.artistname}
            for song in recommendations.recommendations
        ],
    }, ensure_ascii=False)


class RecommendationState(TypedDict):
    request: ConversationRequest
    requested_count: int | None
    target_duration_ms: int | None
    next_count: int
    rounds: int
    recommendations: SongRecommendations | None
    matches: list[SongMatch]
    preview: PlaylistPreview | None


def proposal_for(state: RecommendationState, provider: Literal["spotify", "youtube"]) -> PlaylistProposal:
    recommendations = state["recommendations"]
    if recommendations is None:
        raise ValueError("Recommendations must be generated before matching.")
    return PlaylistProposal.model_validate({
        "provider": provider,
        "name": recommendations.name,
        "description": recommendations.description,
        "songs": [song.model_dump() for song in recommendations.recommendations],
        "requested_count": state["requested_count"],
        "target_duration_ms": state["target_duration_ms"],
    })


async def prepare_recommendations(
    request: ConversationRequest,
    token: str,
    provider: Literal["spotify", "youtube"] = "spotify",
    *,
    service: PlaylistService = playlist_service,
) -> tuple[PlaylistPreview, SongRecommendations]:
    """Keep credentials in a request-local closure, never in model or graph state."""
    count, duration = requested_quantity(request)
    initial_count = count or (min(MAX_CANDIDATES, math.ceil(duration / 150_000) + 5) if duration else 5)

    async def generate(state: RecommendationState) -> dict:
        previous = state["recommendations"]
        excluded = previous.recommendations if previous else []
        result = await run_in_threadpool(generate_candidates, state["request"], state["next_count"], excluded)
        if previous:
            result = previous.model_copy(update={
                "recommendations": [*excluded, *result.recommendations],
            })
        result.requested_count, result.target_duration_ms = count, duration
        return {"recommendations": result, "rounds": state["rounds"] + 1}

    async def resolve(state: RecommendationState) -> dict:
        proposal = proposal_for(state, provider)
        matches = list(state["matches"])
        for song in proposal.songs[len(matches):]:
            matches.append(await service.providers[provider].resolve(song, token))
        return {"matches": matches}

    def assess(state: RecommendationState) -> dict:
        proposal = proposal_for(state, provider)
        selected = service.select_matches(proposal, state["matches"])
        tracks = [match.track for match in selected if match.status == "matched" and match.track]
        total_duration = sum(track.duration_ms or 0 for track in tracks)
        desired_count = count or (None if duration else 5)
        count_ok = bool(tracks) and (desired_count is None or len(tracks) == desired_count)
        duration_ok = duration is None or abs(total_duration - duration) <= 30_000
        if count_ok and duration_ok:
            return {"next_count": 0}
        remaining = MAX_CANDIDATES - len(state["matches"])
        missing = max(1, (desired_count or 0) - len(tracks))
        if duration and not duration_ok:
            missing = max(missing, math.ceil(max(0, duration - total_duration) / 150_000) + 5)
        return {"next_count": min(remaining, missing)}

    def route(state: RecommendationState) -> Literal["generate", "draft"]:
        return "generate" if state["next_count"] and state["rounds"] < MAX_GENERATION_ROUNDS else "draft"

    def draft(state: RecommendationState) -> dict:
        return {"preview": service.prepare_resolved(proposal_for(state, provider), state["matches"], token)}

    builder = StateGraph(RecommendationState)
    builder.add_node("generate", generate)
    builder.add_node("resolve", resolve)
    builder.add_node("assess", assess)
    builder.add_node("draft", draft)
    builder.add_edge(START, "generate")
    builder.add_edge("generate", "resolve")
    builder.add_edge("resolve", "assess")
    builder.add_conditional_edges("assess", route)
    builder.add_edge("draft", END)
    graph = builder.compile()
    initial: RecommendationState = {
        "request": request, "requested_count": count, "target_duration_ms": duration,
        "next_count": initial_count, "rounds": 0, "recommendations": None,
        "matches": [], "preview": None,
    }
    try:
        with tracing_context(enabled=False):
            async with asyncio.timeout(WORKFLOW_TIMEOUT_SECONDS):
                result = await graph.ainvoke(initial, config={"recursion_limit": 16})
    except TimeoutError as exc:
        raise HTTPException(504, "Recommendation matching timed out. Please try a smaller request.") from exc
    return result["preview"], result["recommendations"]