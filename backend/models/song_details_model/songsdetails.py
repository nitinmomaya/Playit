from pydantic import BaseModel, ConfigDict
from music.models import PlaylistMetadata


class SongDetails(BaseModel):
	model_config = ConfigDict(extra="forbid")

	songname: str
	artistname: str
	genre: str
	language: str
	mood: str
	release_date: str


class SongRecommendations(PlaylistMetadata):
	message: str
	recommendations: list[SongDetails]
	requested_count: int | None = None
	target_duration_ms: int | None = None
