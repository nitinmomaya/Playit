"""YouTube adapter for the shared preview/approval workflow.

Search metadata is evidence, not a verified recording identity. Conservative
matching skips alternate versions; ties select the first best search result.
Catalog responses and video IDs are never sent to Gemini.
"""

# Import html.
import html
# Import re.
import re

# Import HTTPException.
from fastapi import HTTPException

# Import PlaylistProposal, RecommendedSong, ResolvedTrack, SongMatch.
from music.models import PlaylistProposal, RecommendedSong, ResolvedTrack, SongMatch
# Import artist_keys, normalize, strip_artist_prefix.
from music.providers import artist_keys, normalize, strip_artist_prefix
# Import web_api.
from youtube import web_api


# Define contains_phrase.
def contains_phrase(text: str, phrase: str) -> bool:
    # Return bool(phrase) and f' {phrase} ' in f' {text} '.
    return bool(phrase) and f" {phrase} " in f" {text} "


# Group the fields/behavior of YouTubeProvider.
class YouTubeProvider:
    # Define resolve as an awaited operation.
    async def resolve(self, song: RecommendedSong, token: str) -> SongMatch:
        # Wait for the operation and keep items.
        items = await web_api.search_videos(f"{song.title} {song.artist}", token)
        # Set requested.
        requested = normalize(strip_artist_prefix(song.title, song.artist))
        # Set editions.
        editions = {"live", "remix", "instrumental", "karaoke", "cover", "acoustic",
                    "slowed", "sped", "lofi", "reprise", "reaction", "tutorial"}
        # Declare candidates.
        candidates: list[tuple[int, dict]] = []
        # Process each item in items.
        for item in items:
            # Set snippet.
            snippet = item.get("snippet", {})
            # Set title.
            title = html.unescape(snippet.get("title", ""))
            # Set channel.
            channel = html.unescape(snippet.get("channelTitle", ""))
            # Set (clean_title, clean_channel).
            clean_title, clean_channel = normalize(title), normalize(channel)
            # Check not contains_phrase(clean_title, requested).
            if not contains_phrase(clean_title, requested):
                continue
            # Check (set(clean_title.split()) & editions) - set(requested.split()).
            if (set(clean_title.split()) & editions) - set(requested.split()):
                continue
            # Check not any((contains_phrase(clean_title, artist) or contains_phrase(clean_chan....
            if not any(contains_phrase(clean_title, artist) or contains_phrase(clean_channel, artist)
                       for artist in artist_keys(song.artist)):
                continue
            # Prefer artist Topic audio, then explicitly labeled official audio.
            score = (3 if clean_channel.endswith(" topic") and any(
                clean_channel.removesuffix(" topic") == artist for artist in artist_keys(song.artist)
            ) else 2 if "official audio" in clean_title else 1 if "official" in clean_title else 0)
            # Call candidates.append.
            candidates.append((score, item))
        # Check not candidates.
        if not candidates:
            # Return SongMatch(recommendation=song, status='not_found').
            return SongMatch(recommendation=song, status="not_found")
        # max preserves the first candidate when scores tie, matching Spotify's
        # first-best policy without relaxing title/artist/version checks.
        _, video = max(candidates, key=lambda candidate: candidate[0])
        # Set snippet.
        snippet = video["snippet"]
        # Set duration.
        duration = video.get("contentDetails", {}).get("duration", "")
        # Set match.
        match = re.fullmatch(r"P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", duration)
        # Set duration_ms.
        duration_ms = None
        # Check match.
        if match:
            # Set (days, hours, minutes, seconds).
            days, hours, minutes, seconds = (float(value or 0) for value in match.groups())
            # Set duration_ms.
            duration_ms = int((days * 86400 + hours * 3600 + minutes * 60 + seconds) * 1000) or None
        # Return SongMatch(recommendation=song, status='matched', track=ResolvedTrack(id=vid....
        return SongMatch(recommendation=song, status="matched", track=ResolvedTrack(
            id=video["id"], uri=f"https://www.youtube.com/watch?v={video['id']}",
            title=html.unescape(snippet["title"]),
            # YouTube exposes uploader/channel, not verified performing artists.
            artists=[html.unescape(snippet.get("channelTitle", "Unknown uploader"))],
            duration_ms=duration_ms,
        ))

    # Define create as an awaited operation.
    async def create(self, proposal: PlaylistProposal, token: str) -> str:
        # Wait for the operation and keep playlist.
        playlist = await web_api.create_playlist(web_api.CreatePlaylist(
            name=proposal.name, description=proposal.description,
            privacy_status="public" if proposal.public else "private",
        ), token)
        # Set playlist_id.
        playlist_id = playlist.get("id")
        # Check not isinstance(playlist_id, str) or not re.fullmatch('[A-Za-z0-9_-]+', play....
        if not isinstance(playlist_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", playlist_id):
            # Stop this request with an explicit HTTP error.
            raise HTTPException(502, "YouTube returned an invalid playlist ID.")
        # Return playlist_id.
        return playlist_id

    # Define add as an awaited operation.
    async def add(self, playlist_id: str, tracks: list[ResolvedTrack], token: str) -> None:
        # Process each track in tracks.
        for track in tracks:
            # Wait for web_api.add_item_to_playlist(playlist_id, web_api.AddItemRequest(video_id=t....
            await web_api.add_item_to_playlist(
                playlist_id, web_api.AddItemRequest(video_id=track.id), token,
            )

    # Define playlist_url.
    def playlist_url(self, playlist_id: str) -> str:
        # Return f'https://www.youtube.com/playlist?list={playlist_id}'.
        return f"https://www.youtube.com/playlist?list={playlist_id}"

# File summary
# - Adapts YouTube videos to the shared music-provider contract.
# - Matches conservative title/artist evidence and parses durations.
# - Creates playlists and adds one video per provider request.
