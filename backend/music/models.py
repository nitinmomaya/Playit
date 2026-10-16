from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, AliasChoices, field_validator


class RecommendedSong(BaseModel):
    """Accept Gemini's existing songname/artistname fields or generic names."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200, validation_alias=AliasChoices("title", "songname"))
    artist: str = Field(min_length=1, max_length=200, validation_alias=AliasChoices("artist", "artistname"))


class PlaylistMetadata(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=300, validate_default=True)

    @field_validator("name", mode="before")
    @classmethod
    def brand_name(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        title = value.strip()
        while title.casefold().endswith("-playit"):
            title = title[:-7].rstrip()
        if not title:
            raise ValueError("A playlist title is required.")
        return f"{title[:93].rstrip()}-Playit"

    @field_validator("description", mode="before")
    @classmethod
    def brand_description(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        description = value.strip()
        suffix = "created via Playit"
        while description.casefold().endswith(suffix.casefold()):
            description = description[:-len(suffix)].rstrip(" .\n")
        description = description[:300 - len(suffix) - 2].rstrip(" .\n")
        return f"{description}. {suffix}" if description else suffix


class PlaylistProposal(PlaylistMetadata):
    provider: Literal["spotify"] = "spotify"
    public: bool = False
    songs: list[RecommendedSong] = Field(min_length=1, max_length=200)
    requested_count: int | None = Field(default=None, ge=1, le=200)
    target_duration_ms: int | None = Field(default=None, ge=60_000, le=28_800_000)


class ResolvedTrack(BaseModel):
    id: str
    uri: str
    title: str
    artists: list[str]
    duration_ms: int | None = Field(default=None, gt=0)


class SongMatch(BaseModel):
    recommendation: RecommendedSong
    status: Literal["matched", "not_found", "ambiguous", "duplicate", "not_selected"]
    track: ResolvedTrack | None = None


class PlaylistResult(BaseModel):
    playlist_id: str
    url: str
    added: int = 0
    total: int
    status: Literal["complete", "partial", "needs_review"] = "partial"


class PlaylistPreview(BaseModel):
    draft_id: str
    proposal: PlaylistProposal
    matches: list[SongMatch]
    matched_count: int
    expires_in: int
    approved: bool
    result: PlaylistResult | None = None
    total_duration_ms: int = 0
    constraint_warning: str | None = None