"""Adapters own catalog matching and provider-specific identifiers."""

# Import re.
import re
# Import unicodedata.
import unicodedata
# Import Protocol.
from typing import Protocol
# Import ratio.
from rapidfuzz.fuzz import ratio

# Import web_api.
from spotify import web_api
# Import PlaylistProposal, RecommendedSong, ResolvedTrack, SongMatch.
from music.models import PlaylistProposal, RecommendedSong, ResolvedTrack, SongMatch


# Group the fields/behavior of MusicProvider.
class MusicProvider(Protocol):
    # Define resolve as an awaited operation.
    async def resolve(self, song: RecommendedSong, token: str) -> SongMatch: ...
    # Define create as an awaited operation.
    async def create(self, proposal: PlaylistProposal, token: str) -> str: ...
    # Define add as an awaited operation.
    async def add(self, playlist_id: str, tracks: list[ResolvedTrack], token: str) -> None: ...
    # Define playlist_url.
    def playlist_url(self, playlist_id: str) -> str: ...


# Define normalize.
def normalize(value: str) -> str:
    # Fold Latin accents without destroying vowel marks in Hindi/other scripts.
    result: list[str] = []
    # Set latin.
    latin = False
    # Process each char in unicodedata.normalize('NFKD', value).casefold().
    for char in unicodedata.normalize("NFKD", value).casefold():
        # Check unicodedata.category(char).startswith('M').
        if unicodedata.category(char).startswith("M"):
            # Check not latin.
            if not latin:
                # Call result.append.
                result.append(char)
        # Check char.isalnum().
        elif char.isalnum():
            # Set latin.
            latin = "LATIN" in unicodedata.name(char, "")
            # Call result.append.
            result.append(char)
        else:
            # Set latin.
            latin = False
            # Call result.append.
            result.append(" ")
    # Return ' '.join(''.join(result).split()).
    return " ".join("".join(result).split())


def title_key(value: str) -> str:
    """Remove catalog decorations, not meaningful edition labels."""
    # Set value.
    value = re.sub(r'\s*[\(\[]\s*(?:from\b|feat\.?\b|ft\.?\b|(?:\d{4}\s+)?remaster(?:ed)?\b)[^\)\]]*[\)\]]',
                   " ", value, flags=re.I)
    # Set value.
    value = re.sub(r'\s+-\s+(?:from\b.*|(?:\d{4}\s+)?remaster(?:ed)?\b.*)$', "", value, flags=re.I)
    # Return normalize(value).
    return normalize(value)


# Define artist_keys.
def artist_keys(value: str) -> set[str]:
    # Set parts.
    parts = re.split(r'\s*(?:,|;|&|/|\bfeat\.?|\bfeaturing\b|\bft\.?|\band\b|\bwith\b)\s*', value, flags=re.I)
    # Return {normalize(part) for part in parts if normalize(part)} | {normalize(value)}.
    return {normalize(part) for part in parts if normalize(part)} | {normalize(value)}


def strip_artist_prefix(title: str, artist: str) -> str:
    """Strip an artist-title separator only when its prefix is a known credit."""
    # Set parts.
    parts = re.split(r'\s+[-–—:]\s+', title, maxsplit=1)
    # Check len(parts) == 2 and parts[1].strip() and (normalize(parts[0]) in artist_key....
    if len(parts) == 2 and parts[1].strip() and normalize(parts[0]) in artist_keys(artist):
        # Return parts[1].strip().
        return parts[1].strip()
    # Return title.
    return title


def spelling_key(value: str) -> str:
    """Limited romanization folding, not a song-specific alias dictionary."""
    # Set value.
    value = normalize(value)
    # Set value.
    value = re.sub(r'chh', 'ch', value)
    # Return re.sub('([a-z])\\1+', '\\1', value).
    return re.sub(r'([a-z])\1+', r'\1', value)


# Define spelling_match.
def spelling_match(candidate: str, requested: str) -> bool:
    # Set (left, right).
    left, right = candidate.split(), requested.split()
    # Long phrases alone can hide one completely different word. Check every
    # corresponding token and do not fuzz single-word or reordered titles.
    if len(left) != len(right) or len(right) < 2:
        # Return False.
        return False
    # Process each (actual, expected) in zip(left, right).
    for actual, expected in zip(left, right):
        # Check actual == expected.
        if actual == expected:
            continue
        # Check min(len(actual), len(expected)) < 4.
        if min(len(actual), len(expected)) < 4:
            # Return False.
            return False
        # Set ordinary_typo.
        ordinary_typo = ratio(actual, expected) >= 90
        # Set romanized.
        romanized = (actual.isascii() and expected.isascii()
                     and ratio(spelling_key(actual), spelling_key(expected)) >= 95)
        # Check not ordinary_typo and (not romanized).
        if not ordinary_typo and not romanized:
            # Return False.
            return False
    # Return True.
    return True


def title_score(name: str, song: RecommendedSong, artists: list[str]) -> int:
    """Prefer exact titles; accept bounded aliases only with artist evidence."""
    # Set candidate.
    candidate = title_key(name)
    # Set requested.
    requested = title_key(strip_artist_prefix(song.title, song.artist))
    # Check candidate == requested.
    if candidate == requested:
        # Return 3.
        return 3
    # Never turn a title extension into permission to select a different version.
    editions = {"live", "remix", "instrumental", "karaoke", "cover", "acoustic",
                "reprise", "remixify", "slowed", "sped", "lofi", "solo", "version"}
    # Check set(candidate.split()) & editions != set(requested.split()) & editions.
    if (set(candidate.split()) & editions) != (set(requested.split()) & editions):
        # Return 0.
        return 0
    # Catalog subtitles may be longer than the normal two-word extension limit.
    # Require an explicit separator and an exact main title, not arbitrary fuzzy
    # similarity. Edition and duet checks still apply before accepting it.
    subtitle_parts = re.split(r'\s+[-–—]\s+', name, maxsplit=1)
    # Set subtitle_match.
    subtitle_match = (
        len(subtitle_parts) == 2
        and len(requested.split()) >= 2
        and title_key(subtitle_parts[0]) == requested
    )
    # Set credited.
    credited = {normalize(artist) for artist in artists}
    # Set requested_artists.
    requested_artists = artist_keys(song.artist)
    # Duet labels represent a legitimate variant only when the user/model
    # supplied multiple singers and all split credits are present in the result.
    without_duet = re.sub(r'\s+duet$', '', candidate)
    # Check without_duet != candidate.
    if without_duet != candidate:
        # Set split_artists.
        split_artists = requested_artists - {normalize(song.artist)}
        # Check len(split_artists) < 2 or not split_artists.issubset(credited).
        if len(split_artists) < 2 or not split_artists.issubset(credited):
            # Return 0.
            return 0
        # Check without_duet == requested.
        if without_duet == requested:
            # Return 2.
            return 2
        # Set candidate.
        candidate = without_duet
    # Check subtitle_match.
    if subtitle_match:
        # Return 2.
        return 2
    # Set (short, long).
    short, long = requested.split(), candidate.split()
    # Contains matching uses complete contiguous words, not raw substrings.
    # Require a multiword phrase, a matching artist (enforced by resolve), and
    # the edition/duet checks above. Exact titles always rank above this match.
    if len(short) >= 2 and any(long[start:start + len(short)] == short
                               for start in range(len(long) - len(short) + 1)):
        # Return 1.
        return 1
    # Set split_artists.
    split_artists = requested_artists - {normalize(song.artist)}
    # Set required_artists.
    required_artists = split_artists or {normalize(song.artist)}
    # Check required_artists.issubset(credited).
    if required_artists.issubset(credited):
        # Compose spelling normalization with contains matching. Previously
        # Ja/Jaa could not match because short changed words were excluded from
        # fuzzy scoring, and fuzzy scoring required equal full-title lengths.
        folded_short = spelling_key(requested).split()
        # Set folded_long.
        folded_long = spelling_key(candidate).split()
        # Check len(folded_short) >= 3 and any((folded_long[start:start + len(folded_short)....
        if len(folded_short) >= 3 and any(
            folded_long[start:start + len(folded_short)] == folded_short
            for start in range(len(folded_long) - len(folded_short) + 1)
        ):
            # Return 1.
            return 1
        # Set main_title.
        main_title = title_key(subtitle_parts[0])
        # Check spelling_match(candidate, requested) or spelling_match(main_title, requested).
        if spelling_match(candidate, requested) or spelling_match(main_title, requested):
            # Return 1.
            return 1
    # Return 0.
    return 0


def same_recording(left: dict, right: dict) -> bool:
    """Collapse reissues only when artist/title and recording evidence agree."""
    # Set left_artists.
    left_artists = {normalize(a["name"]) for a in left["artists"]}
    # Set right_artists.
    right_artists = {normalize(a["name"]) for a in right["artists"]}
    # Check title_key(left['name']) != title_key(right['name']) or not left_artists.int....
    if title_key(left["name"]) != title_key(right["name"]) or not left_artists.intersection(right_artists):
        # Return False.
        return False
    # Set left_isrc.
    left_isrc = (left.get("external_ids") or {}).get("isrc")
    # Set right_isrc.
    right_isrc = (right.get("external_ids") or {}).get("isrc")
    # Check left_isrc and right_isrc.
    if left_isrc and right_isrc:
        # The recording identifier is stronger evidence than a release's
        # composer/singer credit list, which can vary across compilations.
        return left_isrc == right_isrc
    # Check left_artists != right_artists.
    if left_artists != right_artists:
        # Return False.
        return False
    # Set durations.
    durations = left.get("duration_ms"), right.get("duration_ms")
    # Return all((isinstance(d, int) and d > 0 for d in durations)) and abs(durations[0]....
    return all(isinstance(d, int) and d > 0 for d in durations) and abs(durations[0] - durations[1]) <= 2000


def candidate_rank(item: dict, song: RecommendedSong) -> tuple[int, int, int]:
    """Prefer all requested credits, then an original album over a compilation.

    Rank by match quality, not popularity or arbitrary ID. Ties retain Spotify's
    original search order so the first best candidate is selected consistently.
    """
    # Set credited.
    credited = {normalize(a["name"]) for a in item["artists"]}
    # Set coverage.
    coverage = len(artist_keys(song.artist).intersection(credited))
    # Set album_type.
    album_type = (item.get("album") or {}).get("album_type")
    # Return the assembled result to the caller.
    return (title_score(item["name"], song, [a["name"] for a in item["artists"]]),
            coverage, 1 if album_type in ("album", "single") else 0)


# Define best_recordings.
def best_recordings(items: list[dict], song: RecommendedSong) -> list[dict]:
    # Check not items.
    if not items:
        # Return the assembled result to the caller.
        return []
    # Set best_rank.
    best_rank = max(candidate_rank(item, song) for item in items)
    # Declare recordings.
    recordings: list[dict] = []
    # Process each item in items.
    for item in items:
        # Check candidate_rank(item, song) != best_rank.
        if candidate_rank(item, song) != best_rank:
            continue
        # Check not any((same_recording(previous, item) for previous in recordings)).
        if not any(same_recording(previous, item) for previous in recordings):
            # Call recordings.append.
            recordings.append(item)
    # Return recordings.
    return recordings


# Group the fields/behavior of SpotifyProvider.
class SpotifyProvider:
    # Define resolve as an awaited operation.
    async def resolve(self, song: RecommendedSong, token: str) -> SongMatch:
        # Strip filter punctuation supplied by an LLM; do not let it supply URLs or IDs.
        title = strip_artist_prefix(song.title, song.artist).replace('"', " ").replace(":", " ")
        # Set artist.
        artist = song.artist.replace('"', " ").replace(":", " ")
        # Set primary_artist.
        primary_artist = re.split(r',|;|&|/|\bfeat\.?|\bfeaturing\b|\bft\.?|\band\b|\bwith\b', artist, flags=re.I)[0].strip()
        # Set queries.
        queries = list(dict.fromkeys([
            f'track:"{title}" artist:"{artist}"',
            f'{title} {primary_artist}',
            f'track:"{title}"',
            (f'{spelling_key(title)} {primary_artist}'
             if spelling_key(title) != title_key(title) else title_key(title)),
        ]))
        # Declare matches.
        matches: dict[str, ResolvedTrack] = {}
        # Declare candidates.
        candidates: dict[str, dict] = {}
        # Process each query in queries.
        for query in queries:
            # Wait for the operation and keep items.
            items = await web_api.search_tracks(query, token)
            # Process each item in items.
            for item in items:
                # Set track_id.
                track_id = item.get("id", "")
                # Check not isinstance(track_id, str) or not re.fullmatch('[A-Za-z0-9]{22}', track_....
                if not isinstance(track_id, str) or not re.fullmatch(r"[A-Za-z0-9]{22}", track_id):
                    continue
                # Check item.get('is_playable') is False or item.get('restrictions') or item.get('i....
                if item.get("is_playable") is False or item.get("restrictions") or item.get("is_local"):
                    continue
                # Set name.
                name = item.get("name")
                # Set raw_artists.
                raw_artists = item.get("artists")
                # Set artists.
                artists = [a["name"] for a in raw_artists or []
                           if isinstance(a, dict) and isinstance(a.get("name"), str)]
                # Check not isinstance(name, str) or not title_score(name, song, artists) or (not a....
                if (not isinstance(name, str) or not title_score(name, song, artists)
                        or not artist_keys(song.artist).intersection(normalize(a) for a in artists)):
                    continue
                # Store sanitized credit data for ranking and recording grouping.
                candidates[track_id] = {**item, "artists": [{"name": a} for a in artists]}
            # Set matches.
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
                # Return SongMatch(recommendation=song, status='matched', track=next(iter(matches.va....
                return SongMatch(recommendation=song, status="matched", track=next(iter(matches.values())))
        # Check matches.
        if matches:
            # Return SongMatch(recommendation=song, status='matched', track=next(iter(matches.va....
            return SongMatch(recommendation=song, status="matched", track=next(iter(matches.values())))
        # Return SongMatch(recommendation=song, status='not_found').
        return SongMatch(recommendation=song, status="not_found")

    # Define create as an awaited operation.
    async def create(self, proposal: PlaylistProposal, token: str) -> str:
        # Wait for the operation and keep playlist.
        playlist = await web_api.create_playlist("me", web_api.CreatePlaylist(
            name=proposal.name, description=proposal.description, public=proposal.public,
        ), token)
        # Set playlist_id.
        playlist_id = playlist.get("id")
        # Check not isinstance(playlist_id, str) or not re.fullmatch('[A-Za-z0-9]{22}', pla....
        if not isinstance(playlist_id, str) or not re.fullmatch(r"[A-Za-z0-9]{22}", playlist_id):
            # Import HTTPException.
            from fastapi import HTTPException
            # Stop this request with an explicit HTTP error.
            raise HTTPException(status_code=502, detail="Spotify returned an invalid playlist ID.")
        # Return playlist_id.
        return playlist_id

    # Define add as an awaited operation.
    async def add(self, playlist_id: str, tracks: list[ResolvedTrack], token: str) -> None:
        # Wait for web_api.add_item_to_playlist(playlist_id, web_api.AddItemRequest(uris=[trac....
        await web_api.add_item_to_playlist(
            playlist_id, web_api.AddItemRequest(uris=[track.uri for track in tracks]), token,
        )

    # Define playlist_url.
    def playlist_url(self, playlist_id: str) -> str:
        # Return f'https://open.spotify.com/playlist/{playlist_id}'.
        return f"https://open.spotify.com/playlist/{playlist_id}"

# File summary
# - Defines the provider contract and Spotify implementation.
# - Matches titles/credits using bounded normalization and recording evidence.
# - Adapts verified IDs into Spotify create/add operations.
