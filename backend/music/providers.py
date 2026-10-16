"""Adapters own catalog matching and provider-specific identifiers."""

import re
import unicodedata
from typing import Protocol
from rapidfuzz.fuzz import ratio

from spotify import web_api
from music.models import PlaylistProposal, RecommendedSong, ResolvedTrack, SongMatch


class MusicProvider(Protocol):
    async def resolve(self, song: RecommendedSong, token: str) -> SongMatch: ...
    async def create(self, proposal: PlaylistProposal, token: str) -> str: ...
    async def add(self, playlist_id: str, tracks: list[ResolvedTrack], token: str) -> None: ...
    def playlist_url(self, playlist_id: str) -> str: ...


def normalize(value: str) -> str:
    # Fold Latin accents without destroying vowel marks in Hindi/other scripts.
    result: list[str] = []
    latin = False
    for char in unicodedata.normalize("NFKD", value).casefold():
        if unicodedata.category(char).startswith("M"):
            if not latin:
                result.append(char)
        elif char.isalnum():
            latin = "LATIN" in unicodedata.name(char, "")
            result.append(char)
        else:
            latin = False
            result.append(" ")
    return " ".join("".join(result).split())


def title_key(value: str) -> str:
    """Remove catalog decorations, not meaningful edition labels."""
    value = re.sub(r'\s*[\(\[]\s*(?:from\b|feat\.?\b|ft\.?\b|(?:\d{4}\s+)?remaster(?:ed)?\b)[^\)\]]*[\)\]]',
                   " ", value, flags=re.I)
    value = re.sub(r'\s+-\s+(?:from\b.*|(?:\d{4}\s+)?remaster(?:ed)?\b.*)$', "", value, flags=re.I)
    return normalize(value)


def artist_keys(value: str) -> set[str]:
    parts = re.split(r'\s*(?:,|;|&|/|\bfeat\.?|\bfeaturing\b|\bft\.?|\band\b|\bwith\b)\s*', value, flags=re.I)
    return {normalize(part) for part in parts if normalize(part)} | {normalize(value)}


def strip_artist_prefix(title: str, artist: str) -> str:
    """Strip an artist-title separator only when its prefix is a known credit."""
    parts = re.split(r'\s+[-–—:]\s+', title, maxsplit=1)
    if len(parts) == 2 and parts[1].strip() and normalize(parts[0]) in artist_keys(artist):
        return parts[1].strip()
    return title


def spelling_key(value: str) -> str:
    """Limited romanization folding, not a song-specific alias dictionary."""
    value = normalize(value)
    value = re.sub(r'chh', 'ch', value)
    return re.sub(r'([a-z])\1+', r'\1', value)


def spelling_match(candidate: str, requested: str) -> bool:
    left, right = candidate.split(), requested.split()
    # Long phrases alone can hide one completely different word. Check every
    # corresponding token and do not fuzz single-word or reordered titles.
    if len(left) != len(right) or len(right) < 2:
        return False
    for actual, expected in zip(left, right):
        if actual == expected:
            continue
        if min(len(actual), len(expected)) < 4:
            return False
        ordinary_typo = ratio(actual, expected) >= 90
        romanized = (actual.isascii() and expected.isascii()
                     and ratio(spelling_key(actual), spelling_key(expected)) >= 95)
        if not ordinary_typo and not romanized:
            return False
    return True


def title_score(name: str, song: RecommendedSong, artists: list[str]) -> int:
    """Prefer exact titles; accept bounded aliases only with artist evidence."""
    candidate = title_key(name)
    requested = title_key(strip_artist_prefix(song.title, song.artist))
    if candidate == requested:
        return 3
    # Never turn a title extension into permission to select a different version.
    editions = {"live", "remix", "instrumental", "karaoke", "cover", "acoustic",
                "reprise", "remixify", "slowed", "sped", "lofi", "solo", "version"}
    if (set(candidate.split()) & editions) != (set(requested.split()) & editions):
        return 0
    # Catalog subtitles may be longer than the normal two-word extension limit.
    # Require an explicit separator and an exact main title, not arbitrary fuzzy
    # similarity. Edition and duet checks still apply before accepting it.
    subtitle_parts = re.split(r'\s+[-–—]\s+', name, maxsplit=1)
    subtitle_match = (
        len(subtitle_parts) == 2
        and len(requested.split()) >= 2
        and title_key(subtitle_parts[0]) == requested
    )
    credited = {normalize(artist) for artist in artists}
    requested_artists = artist_keys(song.artist)
    # Duet labels represent a legitimate variant only when the user/model
    # supplied multiple singers and all split credits are present in the result.
    without_duet = re.sub(r'\s+duet$', '', candidate)
    if without_duet != candidate:
        split_artists = requested_artists - {normalize(song.artist)}
        if len(split_artists) < 2 or not split_artists.issubset(credited):
            return 0
        if without_duet == requested:
            return 2
        candidate = without_duet
    if subtitle_match:
        return 2
    short, long = requested.split(), candidate.split()
    # Contains matching uses complete contiguous words, not raw substrings.
    # Require a multiword phrase, a matching artist (enforced by resolve), and
    # the edition/duet checks above. Exact titles always rank above this match.
    if len(short) >= 2 and any(long[start:start + len(short)] == short
                               for start in range(len(long) - len(short) + 1)):
        return 1
    split_artists = requested_artists - {normalize(song.artist)}
    required_artists = split_artists or {normalize(song.artist)}
    if required_artists.issubset(credited):
        # Compose spelling normalization with contains matching. Previously
        # Ja/Jaa could not match because short changed words were excluded from
        # fuzzy scoring, and fuzzy scoring required equal full-title lengths.
        folded_short = spelling_key(requested).split()
        folded_long = spelling_key(candidate).split()
        if len(folded_short) >= 3 and any(
            folded_long[start:start + len(folded_short)] == folded_short
            for start in range(len(folded_long) - len(folded_short) + 1)
        ):
            return 1
        main_title = title_key(subtitle_parts[0])
        if spelling_match(candidate, requested) or spelling_match(main_title, requested):
            return 1
    return 0


def same_recording(left: dict, right: dict) -> bool:
    """Collapse reissues only when artist/title and recording evidence agree."""
    left_artists = {normalize(a["name"]) for a in left["artists"]}
    right_artists = {normalize(a["name"]) for a in right["artists"]}
    if title_key(left["name"]) != title_key(right["name"]) or not left_artists.intersection(right_artists):
        return False
    left_isrc = (left.get("external_ids") or {}).get("isrc")
    right_isrc = (right.get("external_ids") or {}).get("isrc")
    if left_isrc and right_isrc:
        # The recording identifier is stronger evidence than a release's
        # composer/singer credit list, which can vary across compilations.
        return left_isrc == right_isrc
    if left_artists != right_artists:
        return False
    durations = left.get("duration_ms"), right.get("duration_ms")
    return all(isinstance(d, int) and d > 0 for d in durations) and abs(durations[0] - durations[1]) <= 2000


def candidate_rank(item: dict, song: RecommendedSong) -> tuple[int, int, int]:
    """Prefer all requested credits, then an original album over a compilation.

    Rank by match quality, not popularity or arbitrary ID. Ties retain Spotify's
    original search order so the first best candidate is selected consistently.
    """
    credited = {normalize(a["name"]) for a in item["artists"]}
    coverage = len(artist_keys(song.artist).intersection(credited))
    album_type = (item.get("album") or {}).get("album_type")
    return (title_score(item["name"], song, [a["name"] for a in item["artists"]]),
            coverage, 1 if album_type in ("album", "single") else 0)


def best_recordings(items: list[dict], song: RecommendedSong) -> list[dict]:
    if not items:
        return []
    best_rank = max(candidate_rank(item, song) for item in items)
    recordings: list[dict] = []
    for item in items:
        if candidate_rank(item, song) != best_rank:
            continue
        if not any(same_recording(previous, item) for previous in recordings):
            recordings.append(item)
    return recordings


class SpotifyProvider:
    async def resolve(self, song: RecommendedSong, token: str) -> SongMatch:
        # Strip filter punctuation supplied by an LLM; do not let it supply URLs or IDs.
        title = strip_artist_prefix(song.title, song.artist).replace('"', " ").replace(":", " ")
        artist = song.artist.replace('"', " ").replace(":", " ")
        primary_artist = re.split(r',|;|&|/|\bfeat\.?|\bfeaturing\b|\bft\.?|\band\b|\bwith\b', artist, flags=re.I)[0].strip()
        queries = list(dict.fromkeys([
            f'track:"{title}" artist:"{artist}"',
            f'{title} {primary_artist}',
            f'track:"{title}"',
            (f'{spelling_key(title)} {primary_artist}'
             if spelling_key(title) != title_key(title) else title_key(title)),
        ]))
        matches: dict[str, ResolvedTrack] = {}
        candidates: dict[str, dict] = {}
        for query in queries:
            items = await web_api.search_tracks(query, token)
            for item in items:
                track_id = item.get("id", "")
                if not isinstance(track_id, str) or not re.fullmatch(r"[A-Za-z0-9]{22}", track_id):
                    continue
                if item.get("is_playable") is False or item.get("restrictions") or item.get("is_local"):
                    continue
                name = item.get("name")
                raw_artists = item.get("artists")
                artists = [a["name"] for a in raw_artists or []
                           if isinstance(a, dict) and isinstance(a.get("name"), str)]
                if (not isinstance(name, str) or not title_score(name, song, artists)
                        or not artist_keys(song.artist).intersection(normalize(a) for a in artists)):
                    continue
                # Store sanitized credit data for ranking and recording grouping.
                candidates[track_id] = {**item, "artists": [{"name": a} for a in artists]}
            matches = {
                item["id"]: ResolvedTrack(
                    id=item["id"], uri=f'spotify:track:{item["id"]}',
                    title=item["name"], artists=[a["name"] for a in item["artists"]],
                    duration_ms=item.get("duration_ms"),
                ) for item in best_recordings(list(candidates.values()), song)
            }
            # Alias matches wait for remaining searches: an exact title found
            # later must take precedence over a longer, merely plausible title.
            if matches and title_score(next(iter(matches.values())).title, song,
                                                next(iter(matches.values())).artists) == 3:
                return SongMatch(recommendation=song, status="matched", track=next(iter(matches.values())))
        if matches:
            return SongMatch(recommendation=song, status="matched", track=next(iter(matches.values())))
        return SongMatch(recommendation=song, status="not_found")

    async def create(self, proposal: PlaylistProposal, token: str) -> str:
        playlist = await web_api.create_playlist("me", web_api.CreatePlaylist(
            name=proposal.name, description=proposal.description, public=proposal.public,
        ), token)
        playlist_id = playlist.get("id")
        if not isinstance(playlist_id, str) or not re.fullmatch(r"[A-Za-z0-9]{22}", playlist_id):
            from fastapi import HTTPException
            raise HTTPException(status_code=502, detail="Spotify returned an invalid playlist ID.")
        return playlist_id

    async def add(self, playlist_id: str, tracks: list[ResolvedTrack], token: str) -> None:
        await web_api.add_item_to_playlist(
            playlist_id, web_api.AddItemRequest(uris=[track.uri for track in tracks]), token,
        )

    def playlist_url(self, playlist_id: str) -> str:
        return f"https://open.spotify.com/playlist/{playlist_id}"