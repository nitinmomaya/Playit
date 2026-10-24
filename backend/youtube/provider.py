"""YouTube adapter for the shared preview/approval workflow.

Search metadata is evidence, not a verified recording identity. Conservative
matching skips alternate versions; ties select the first best search result.
Catalog responses and video IDs are never sent to Gemini.
"""

import html
import re

from fastapi import HTTPException

from music.models import PlaylistProposal, RecommendedSong, ResolvedTrack, SongMatch
from music.providers import artist_keys, normalize, strip_artist_prefix
from youtube import web_api


def contains_phrase(text: str, phrase: str) -> bool:
    return bool(phrase) and f" {phrase} " in f" {text} "


class YouTubeProvider:
    async def resolve(self, song: RecommendedSong, token: str) -> SongMatch:
        items = await web_api.search_videos(f"{song.title} {song.artist}", token)
        requested = normalize(strip_artist_prefix(song.title, song.artist))
        editions = {"live", "remix", "instrumental", "karaoke", "cover", "acoustic",
                    "slowed", "sped", "lofi", "reprise", "reaction", "tutorial"}
        candidates: list[tuple[int, dict]] = []
        for item in items:
            snippet = item.get("snippet", {})
            title = html.unescape(snippet.get("title", ""))
            channel = html.unescape(snippet.get("channelTitle", ""))
            clean_title, clean_channel = normalize(title), normalize(channel)
            if not contains_phrase(clean_title, requested):
                continue
            if (set(clean_title.split()) & editions) - set(requested.split()):
                continue
            if not any(contains_phrase(clean_title, artist) or contains_phrase(clean_channel, artist)
                       for artist in artist_keys(song.artist)):
                continue
            # Prefer artist Topic audio, then explicitly labeled official audio.
            score = (3 if clean_channel.endswith(" topic") and any(
                clean_channel.removesuffix(" topic") == artist for artist in artist_keys(song.artist)
            ) else 2 if "official audio" in clean_title else 1 if "official" in clean_title else 0)
            candidates.append((score, item))
        if not candidates:
            return SongMatch(recommendation=song, status="not_found")
        # max preserves the first candidate when scores tie, matching Spotify's
        # first-best policy without relaxing title/artist/version checks.
        _, video = max(candidates, key=lambda candidate: candidate[0])
        snippet = video["snippet"]
        duration = video.get("contentDetails", {}).get("duration", "")
        match = re.fullmatch(r"P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", duration)
        duration_ms = None
        if match:
            days, hours, minutes, seconds = (float(value or 0) for value in match.groups())
            duration_ms = int((days * 86400 + hours * 3600 + minutes * 60 + seconds) * 1000) or None
        return SongMatch(recommendation=song, status="matched", track=ResolvedTrack(
            id=video["id"], uri=f"https://www.youtube.com/watch?v={video['id']}",
            title=html.unescape(snippet["title"]),
            # YouTube exposes uploader/channel, not verified performing artists.
            artists=[html.unescape(snippet.get("channelTitle", "Unknown uploader"))],
            duration_ms=duration_ms,
        ))

    async def create(self, proposal: PlaylistProposal, token: str) -> str:
        playlist = await web_api.create_playlist(web_api.CreatePlaylist(
            name=proposal.name, description=proposal.description,
            privacy_status="public" if proposal.public else "private",
        ), token)
        playlist_id = playlist.get("id")
        if not isinstance(playlist_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", playlist_id):
            raise HTTPException(502, "YouTube returned an invalid playlist ID.")
        return playlist_id

    async def add(self, playlist_id: str, tracks: list[ResolvedTrack], token: str) -> None:
        for track in tracks:
            await web_api.add_item_to_playlist(
                playlist_id, web_api.AddItemRequest(video_id=track.id), token,
            )

    def playlist_url(self, playlist_id: str) -> str:
        return f"https://www.youtube.com/playlist?list={playlist_id}"