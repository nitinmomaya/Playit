"""LangGraph owns bounded generate, resolve, assess, and draft transitions."""

# Import asyncio.
import asyncio
# Import json.
import json
# Import math.
import math
# Import Literal, TypedDict.
from typing import Literal, TypedDict

# Import HTTPException.
from fastapi import HTTPException
# Import run_in_threadpool.
from fastapi.concurrency import run_in_threadpool
# Import END, START, StateGraph.
from langgraph.graph import END, START, StateGraph
# Import tracing_context.
from langsmith import tracing_context

# Import ConversationRequest.
from gemini_setup.conversation import ConversationRequest
# Import SongRecommendations.
from models.song_details_model.songsdetails import SongRecommendations
# Import requested_quantity.
from music.constraints import requested_quantity
# Import PlaylistPreview, PlaylistProposal, SongMatch.
from music.models import PlaylistPreview, PlaylistProposal, SongMatch
# Import PlaylistService, playlist_service.
from music.service import PlaylistService, playlist_service
# Import generate_candidates.
from recommendations.langchain_model import generate_candidates

# Set MAX_GENERATION_ROUNDS.
MAX_GENERATION_ROUNDS = 3
# Set MAX_CANDIDATES.
MAX_CANDIDATES = 200
# Set WORKFLOW_TIMEOUT_SECONDS.
WORKFLOW_TIMEOUT_SECONDS = 120


def recommendation_context(recommendations: SongRecommendations) -> str:
    """Only independently generated suggestions may enter future model history."""
    # Return json.dumps({'message': recommendations.message, 'name': recommendations.nam....
    return json.dumps({
        "message": recommendations.message,
        "name": recommendations.name,
        "description": recommendations.description,
        "recommendations": [
            {"songname": song.songname, "artistname": song.artistname}
            for song in recommendations.recommendations
        ],
    }, ensure_ascii=False)


# Group the fields/behavior of RecommendationState.
class RecommendationState(TypedDict):
    # Declare request.
    request: ConversationRequest
    # Declare requested_count.
    requested_count: int | None
    # Declare target_duration_ms.
    target_duration_ms: int | None
    # Declare next_count.
    next_count: int
    # Declare rounds.
    rounds: int
    # Declare recommendations.
    recommendations: SongRecommendations | None
    # Declare matches.
    matches: list[SongMatch]
    # Declare preview.
    preview: PlaylistPreview | None


# Define proposal_for.
def proposal_for(state: RecommendationState, provider: Literal["spotify", "youtube"]) -> PlaylistProposal:
    # Set recommendations.
    recommendations = state["recommendations"]
    # Check recommendations is None.
    if recommendations is None:
        # Propagate this failure instead of continuing.
        raise ValueError("Recommendations must be generated before matching.")
    # Return PlaylistProposal.model_validate({'provider': provider, 'name': recommendati....
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
    # Set (count, duration).
    count, duration = requested_quantity(request)
    # Set initial_count.
    initial_count = count or (min(MAX_CANDIDATES, math.ceil(duration / 150_000) + 5) if duration else 5)

    # Define generate as an awaited operation.
    async def generate(state: RecommendationState) -> dict:
        # Set previous.
        previous = state["recommendations"]
        # Set excluded.
        excluded = previous.recommendations if previous else []
        # Wait for the operation and keep result.
        result = await run_in_threadpool(generate_candidates, state["request"], state["next_count"], excluded)
        # Check previous.
        if previous:
            # Set result.
            result = previous.model_copy(update={
                "recommendations": [*excluded, *result.recommendations],
            })
        # Set (result.requested_count, result.target_duration_ms).
        result.requested_count, result.target_duration_ms = count, duration
        # Return the assembled result to the caller.
        return {"recommendations": result, "rounds": state["rounds"] + 1}

    # Define resolve as an awaited operation.
    async def resolve(state: RecommendationState) -> dict:
        # Set proposal.
        proposal = proposal_for(state, provider)
        # Set matches.
        matches = list(state["matches"])
        # Process each song in proposal.songs[len(matches):].
        for song in proposal.songs[len(matches):]:
            # Call matches.append.
            matches.append(await service.providers[provider].resolve(song, token))
        # Return the assembled result to the caller.
        return {"matches": matches}

    # Define assess.
    def assess(state: RecommendationState) -> dict:
        # Set proposal.
        proposal = proposal_for(state, provider)
        # Set selected.
        selected = service.select_matches(proposal, state["matches"])
        # Set tracks.
        tracks = [match.track for match in selected if match.status == "matched" and match.track]
        # Set total_duration.
        total_duration = sum(track.duration_ms or 0 for track in tracks)
        # Set desired_count.
        desired_count = count or (None if duration else 5)
        # Set count_ok.
        count_ok = bool(tracks) and (desired_count is None or len(tracks) == desired_count)
        # Set duration_ok.
        duration_ok = duration is None or abs(total_duration - duration) <= 30_000
        # Check count_ok and duration_ok.
        if count_ok and duration_ok:
            # Return the assembled result to the caller.
            return {"next_count": 0}
        # Set remaining.
        remaining = MAX_CANDIDATES - len(state["matches"])
        # Set missing.
        missing = max(1, (desired_count or 0) - len(tracks))
        # Check duration and (not duration_ok).
        if duration and not duration_ok:
            # Set missing.
            missing = max(missing, math.ceil(max(0, duration - total_duration) / 150_000) + 5)
        # Return the assembled result to the caller.
        return {"next_count": min(remaining, missing)}

    # Define route.
    def route(state: RecommendationState) -> Literal["generate", "draft"]:
        # Return 'generate' if state['next_count'] and state['rounds'] < MAX_GENERATION_ROUN....
        return "generate" if state["next_count"] and state["rounds"] < MAX_GENERATION_ROUNDS else "draft"

    # Define draft.
    def draft(state: RecommendationState) -> dict:
        # Return the assembled result to the caller.
        return {"preview": service.prepare_resolved(proposal_for(state, provider), state["matches"], token)}

    # Set builder.
    builder = StateGraph(RecommendationState)
    # Call builder.add_node.
    builder.add_node("generate", generate)
    # Call builder.add_node.
    builder.add_node("resolve", resolve)
    # Call builder.add_node.
    builder.add_node("assess", assess)
    # Call builder.add_node.
    builder.add_node("draft", draft)
    # Call builder.add_edge.
    builder.add_edge(START, "generate")
    # Call builder.add_edge.
    builder.add_edge("generate", "resolve")
    # Call builder.add_edge.
    builder.add_edge("resolve", "assess")
    # Call builder.add_conditional_edges.
    builder.add_conditional_edges("assess", route)
    # Call builder.add_edge.
    builder.add_edge("draft", END)
    # Set graph.
    graph = builder.compile()
    # Declare initial.
    initial: RecommendationState = {
        "request": request, "requested_count": count, "target_duration_ms": duration,
        "next_count": initial_count, "rounds": 0, "recommendations": None,
        "matches": [], "preview": None,
    }
    # Handle failures from this operation below.
    try:
        # Manage tracing_context(enabled=False) with automatic cleanup.
        with tracing_context(enabled=False):
            # Manage asyncio.timeout(WORKFLOW_TIMEOUT_SECONDS) with automatic cleanup.
            async with asyncio.timeout(WORKFLOW_TIMEOUT_SECONDS):
                # Wait for the operation and keep result.
                result = await graph.ainvoke(initial, config={"recursion_limit": 16})
    except TimeoutError as exc:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(504, "Recommendation matching timed out. Please try a smaller request.") from exc
    # Return the assembled result to the caller.
    return result["preview"], result["recommendations"]

# File summary
# - Runs generate, resolve, assess, and draft graph nodes.
# - Reuses old matches and repairs shortfalls within fixed budgets.
# - Keeps credentials outside graph state and never approves writes.
