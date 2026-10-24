"""Compatibility entry point for the existing recommendations endpoint."""

import math

from gemini_setup.conversation import ConversationRequest
from models.song_details_model.songsdetails import SongRecommendations
from music.constraints import requested_quantity
from recommendations.langchain_model import generate_candidates

RecommendationRequest = ConversationRequest


def recommend_songs(request: RecommendationRequest) -> SongRecommendations:
    count, duration = requested_quantity(request)
    candidate_count = count or (min(200, math.ceil(duration / 150_000) + 5) if duration else 5)
    result = generate_candidates(request, candidate_count)
    result.requested_count, result.target_duration_ms = count, duration
    return result

