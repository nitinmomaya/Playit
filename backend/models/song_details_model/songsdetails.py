from pydantic import BaseModel, ConfigDict


class SongDetails(BaseModel):
	model_config = ConfigDict(extra="forbid")

	songname: str
	artistname: str
	genre: str
	language: str
	mood: str
	release_date: str


class SongRecommendations(BaseModel):
	message: str
	recommendations: list[SongDetails]
