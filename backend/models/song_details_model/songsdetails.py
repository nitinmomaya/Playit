# Import BaseModel, ConfigDict.
from pydantic import BaseModel, ConfigDict
# Import PlaylistMetadata.
from music.models import PlaylistMetadata


# Group the fields/behavior of SongDetails.
class SongDetails(BaseModel):
 # Set model_config.
	model_config = ConfigDict(extra="forbid")

 # Declare songname.
	songname: str
 # Declare artistname.
	artistname: str
 # Declare genre.
	genre: str
 # Declare language.
	language: str
 # Declare mood.
	mood: str
 # Declare release_date.
	release_date: str


# Group the fields/behavior of SongRecommendations.
class SongRecommendations(PlaylistMetadata):
 # Declare message.
	message: str
 # Declare recommendations.
	recommendations: list[SongDetails]
 # Declare requested_count.
	requested_count: int | None = None
 # Declare target_duration_ms.
	target_duration_ms: int | None = None

# File summary
# - Defines model-generated song metadata and recommendation output.
# - Shares final playlist metadata validation with the music models.
