# Import Literal.
from typing import Literal

# Import BaseModel, ConfigDict, Field, AliasChoices, field_validator.
from pydantic import BaseModel, ConfigDict, Field, AliasChoices, field_validator


class RecommendedSong(BaseModel):
    """Accept Gemini's existing songname/artistname fields or generic names."""

    # Set model_config.
    model_config = ConfigDict(str_strip_whitespace=True)

    # Validate/configure title.
    title: str = Field(min_length=1, max_length=200, validation_alias=AliasChoices("title", "songname"))
    # Validate/configure artist.
    artist: str = Field(min_length=1, max_length=200, validation_alias=AliasChoices("artist", "artistname"))


# Group the fields/behavior of PlaylistMetadata.
class PlaylistMetadata(BaseModel):
    # Set model_config.
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    # Validate/configure name.
    name: str = Field(min_length=1, max_length=100)
    # Validate/configure description.
    description: str = Field(default="", max_length=300, validate_default=True)

    # Define brand_name.
    @field_validator("name", mode="before")
    @classmethod
    def brand_name(cls, value: object) -> object:
        # Check not isinstance(value, str).
        if not isinstance(value, str):
            # Return value.
            return value
        # Set title.
        title = value.strip()
        # Repeat while title.casefold().endswith('-playit').
        while title.casefold().endswith("-playit"):
            # Set title.
            title = title[:-7].rstrip()
        # Check not title.
        if not title:
            # Propagate this failure instead of continuing.
            raise ValueError("A playlist title is required.")
        # Return f'{title[:93].rstrip()}-Playit'.
        return f"{title[:93].rstrip()}-Playit"

    # Define brand_description.
    @field_validator("description", mode="before")
    @classmethod
    def brand_description(cls, value: object) -> object:
        # Check not isinstance(value, str).
        if not isinstance(value, str):
            # Return value.
            return value
        # Set description.
        description = value.strip()
        # Set suffix.
        suffix = "created via Playit"
        # Repeat while description.casefold().endswith(suffix.casefold()).
        while description.casefold().endswith(suffix.casefold()):
            # Set description.
            description = description[:-len(suffix)].rstrip(" .\n")
        # Set description.
        description = description[:300 - len(suffix) - 2].rstrip(" .\n")
        # Return f'{description}. {suffix}' if description else suffix.
        return f"{description}. {suffix}" if description else suffix


# Group the fields/behavior of PlaylistProposal.
class PlaylistProposal(PlaylistMetadata):
    # Declare provider.
    provider: Literal["spotify", "youtube"] = "spotify"
    # Declare public.
    public: bool = False
    # Validate/configure songs.
    songs: list[RecommendedSong] = Field(min_length=1, max_length=200)
    # Validate/configure requested_count.
    requested_count: int | None = Field(default=None, ge=1, le=200)
    # Validate/configure target_duration_ms.
    target_duration_ms: int | None = Field(default=None, ge=60_000, le=28_800_000)


# Group the fields/behavior of ResolvedTrack.
class ResolvedTrack(BaseModel):
    # Declare id.
    id: str
    # Declare uri.
    uri: str
    # Declare title.
    title: str
    # Declare artists.
    artists: list[str]
    # Validate/configure duration_ms.
    duration_ms: int | None = Field(default=None, gt=0)


# Group the fields/behavior of SongMatch.
class SongMatch(BaseModel):
    # Declare recommendation.
    recommendation: RecommendedSong
    # Declare status.
    status: Literal["matched", "not_found", "ambiguous", "duplicate", "not_selected"]
    # Declare track.
    track: ResolvedTrack | None = None


# Group the fields/behavior of PlaylistResult.
class PlaylistResult(BaseModel):
    # Declare playlist_id.
    playlist_id: str
    # Declare url.
    url: str
    # Declare added.
    added: int = 0
    # Declare total.
    total: int
    # Declare status.
    status: Literal["complete", "partial", "needs_review"] = "partial"


# Group the fields/behavior of PlaylistPreview.
class PlaylistPreview(BaseModel):
    # Declare draft_id.
    draft_id: str
    # Declare proposal.
    proposal: PlaylistProposal
    # Declare matches.
    matches: list[SongMatch]
    # Declare matched_count.
    matched_count: int
    # Declare expires_in.
    expires_in: int
    # Declare approved.
    approved: bool
    # Declare result.
    result: PlaylistResult | None = None
    # Declare total_duration_ms.
    total_duration_ms: int = 0
    # Declare constraint_warning.
    constraint_warning: str | None = None


# Group the fields/behavior of RecommendationPreview.
class RecommendationPreview(BaseModel):
    # Declare preview.
    preview: PlaylistPreview
    # Declare context_text.
    context_text: str

# File summary
# - Defines proposals, catalog matches, previews, and creation results.
# - Validates provider/count/duration and metadata bounds.
# - Applies Playit naming/description branding consistently.
