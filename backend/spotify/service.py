"""Compatibility entry point for the existing recommendations endpoint."""

# Import math.
import math

# Import ConversationRequest.
from gemini_setup.conversation import ConversationRequest
# Import SongRecommendations.
from models.song_details_model.songsdetails import SongRecommendations
# Import requested_quantity.
from music.constraints import requested_quantity
# Import generate_candidates.
from recommendations.langchain_model import generate_candidates

# Set RecommendationRequest.
RecommendationRequest = ConversationRequest


# Define recommend_songs.
def recommend_songs(request: RecommendationRequest) -> SongRecommendations:
    # Set (count, duration).
    count, duration = requested_quantity(request)
    # Set candidate_count.
    candidate_count = count or (min(200, math.ceil(duration / 150_000) + 5) if duration else 5)
    # Set result.
    result = generate_candidates(request, candidate_count)
    # Set (result.requested_count, result.target_duration_ms).
    result.requested_count, result.target_duration_ms = count, duration
    # Return result.
    return result

# File summary
# - Keeps the legacy recommendations-only API compatible.
# - Extracts user quantities and invokes structured LangChain generation.
# - Does not run catalog matching or the graph repair loop.
