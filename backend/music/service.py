"""Short-lived, owner-bound drafts. Spotify catalog data never goes to Gemini."""

# Import asyncio.
import asyncio
# Import hashlib.
import hashlib
# Import secrets.
import secrets
# Import time.
import time
# Import dataclass, field.
from dataclasses import dataclass, field

# Import HTTPException.
from fastapi import HTTPException

# Import PlaylistPreview, PlaylistProposal, PlaylistResult, SongMatch.
from music.models import PlaylistPreview, PlaylistProposal, PlaylistResult, SongMatch
# Import MusicProvider, SpotifyProvider.
from music.providers import MusicProvider, SpotifyProvider
# Import YouTubeProvider.
from youtube.provider import YouTubeProvider

# Set DRAFT_TTL.
DRAFT_TTL = 15 * 60
# Set SESSION_TTL.
SESSION_TTL = 50 * 60
# Set MAX_ENTRIES.
MAX_ENTRIES = 500


# Group the fields/behavior of Draft.
@dataclass
class Draft:
    # Declare owner.
    owner: str
    # Declare proposal.
    proposal: PlaylistProposal
    # Declare matches.
    matches: list[SongMatch]
    # Declare expires_at.
    expires_at: float
    # Declare approved.
    approved: bool = False
    # Declare result.
    result: PlaylistResult | None = None
    # Declare lock.
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


# Group the fields/behavior of PlaylistService.
class PlaylistService:
    # Define __init__.
    def __init__(self) -> None:
        # Declare self.providers.
        self.providers: dict[str, MusicProvider] = {
            "spotify": SpotifyProvider(), "youtube": YouTubeProvider(),
        }
        # Declare self.drafts.
        self.drafts: dict[str, Draft] = {}
        # Declare self.sessions.
        self.sessions: dict[str, tuple[str, float]] = {}

    # Define prune.
    def prune(self) -> None:
        # Set now.
        now = time.monotonic()
        # Set self.drafts.
        self.drafts = {key: value for key, value in self.drafts.items()
                       if value.expires_at > now or value.lock.locked()}
        # Set self.sessions.
        self.sessions = {key: value for key, value in self.sessions.items() if value[1] > now}

    # Define connect.
    def connect(self, token: str) -> str:
        # Call self.prune.
        self.prune()
        # Check len(self.sessions) >= MAX_ENTRIES.
        if len(self.sessions) >= MAX_ENTRIES:
            # Stop this request with an explicit HTTP error.
            raise HTTPException(status_code=503, detail="Too many active music sessions.")
        # Set session_id.
        session_id = secrets.token_urlsafe(32)
        # Set self.sessions[session_id].
        self.sessions[session_id] = (token, time.monotonic() + SESSION_TTL)
        # Return session_id.
        return session_id

    # Define session_token.
    def session_token(self, session_id: str) -> str:
        # Call self.prune.
        self.prune()
        # Set session.
        session = self.sessions.get(session_id)
        # Check session is None.
        if session is None:
            # Stop this request with an explicit HTTP error.
            raise HTTPException(status_code=401, detail="Music session is invalid or expired.")
        # Return session[0].
        return session[0]

    # Define owner.
    @staticmethod
    def owner(token: str) -> str:
        # Return hashlib.sha256(token.encode()).hexdigest().
        return hashlib.sha256(token.encode()).hexdigest()

    # Define draft.
    def draft(self, draft_id: str, token: str) -> Draft:
        # Call self.prune.
        self.prune()
        # Set draft.
        draft = self.drafts.get(draft_id)
        # Check draft is None or not secrets.compare_digest(draft.owner, self.owner(token)).
        if draft is None or not secrets.compare_digest(draft.owner, self.owner(token)):
            # Stop this request with an explicit HTTP error.
            raise HTTPException(status_code=404, detail="Playlist draft not found or expired.")
        # Return draft.
        return draft

    # Define prepare as an awaited operation.
    async def prepare(self, proposal: PlaylistProposal, token: str) -> PlaylistPreview:
        # Call self.prune.
        self.prune()
        # Check len(self.drafts) >= MAX_ENTRIES.
        if len(self.drafts) >= MAX_ENTRIES:
            # Stop this request with an explicit HTTP error.
            raise HTTPException(status_code=503, detail="Too many active playlist drafts.")
        # Set provider.
        provider = self.providers[proposal.provider]
        # Declare matches.
        matches: list[SongMatch] = []
        # Process each song in proposal.songs.
        for song in proposal.songs:
            # Call matches.append.
            matches.append(await provider.resolve(song, token))
        # Return self.prepare_resolved(proposal, matches, token).
        return self.prepare_resolved(proposal, matches, token)

    @staticmethod
    def select_matches(proposal: PlaylistProposal, matches: list[SongMatch]) -> list[SongMatch]:
        """Select verified tracks without mutating the graph's reusable matches."""
        # Set matches.
        matches = [match.model_copy(deep=True) for match in matches]
        # Declare seen.
        seen: set[str] = set()
        # Process each match in matches.
        for match in matches:
            # Check match.track.
            if match.track:
                # Check match.track.id in seen.
                if match.track.id in seen:
                    # Set match.status.
                    match.status = "duplicate"
                # Call seen.add.
                seen.add(match.track.id)
        # Check proposal.target_duration_ms.
        if proposal.target_duration_ms:
            # Bounded subset-sum in five-second units; Spotify durations stay
            # server-side. Whole songs cannot generally sum to an exact time.
            target = round(proposal.target_duration_ms / 5000)
            # Declare states.
            states: dict[tuple[int, int], tuple[int, ...]] = {(0, 0): ()}
            # Process each (index, match) in enumerate(matches).
            for index, match in enumerate(matches):
                # Check match.status != 'matched' or not match.track or (not match.track.duration_ms).
                if match.status != "matched" or not match.track or not match.track.duration_ms:
                    continue
                # Set units.
                units = max(1, round(match.track.duration_ms / 5000))
                # Process each ((total, size), selected) in list(states.items()).
                for (total, size), selected in list(states.items()):
                    # Set next_total.
                    next_total = total + units
                    # Check next_total <= target + 120 and (not proposal.requested_count or len(selecte....
                    if next_total <= target + 120 and (not proposal.requested_count or len(selected) < proposal.requested_count):
                        # Call states.setdefault.
                        states.setdefault((next_total, size + 1 if proposal.requested_count else 0), (*selected, index))
            # Set options.
            options = [(total, selected) for (total, _), selected in states.items() if selected
                       and (not proposal.requested_count or len(selected) == proposal.requested_count)]
            # Set selected.
            selected = set(min(options, key=lambda item: abs(item[0] - target))[1]) if options else set()
            # Process each (index, match) in enumerate(matches).
            for index, match in enumerate(matches):
                # Check match.status == 'matched' and index not in selected.
                if match.status == "matched" and index not in selected:
                    # Set match.status.
                    match.status = "not_selected"
        # Return matches.
        return matches

    def prepare_resolved(self, proposal: PlaylistProposal, matches: list[SongMatch], token: str) -> PlaylistPreview:
        """Store server-verified matches; never exposed as an HTTP or model tool."""
        # Call self.prune.
        self.prune()
        # Check len(self.drafts) >= MAX_ENTRIES.
        if len(self.drafts) >= MAX_ENTRIES:
            # Stop this request with an explicit HTTP error.
            raise HTTPException(status_code=503, detail="Too many active playlist drafts.")
        # Set draft_id.
        draft_id = secrets.token_urlsafe(24)
        # Set selected.
        selected = self.select_matches(proposal, matches)
        # Set self.drafts[draft_id].
        self.drafts[draft_id] = Draft(self.owner(token), proposal, selected, time.monotonic() + DRAFT_TTL)
        # Return self.preview(draft_id, token).
        return self.preview(draft_id, token)

    # Define preview.
    def preview(self, draft_id: str, token: str) -> PlaylistPreview:
        # Set draft.
        draft = self.draft(draft_id, token)
        # Set selected.
        selected = [match.track for match in draft.matches if match.status == "matched" and match.track]
        # Set duration.
        duration = sum(track.duration_ms or 0 for track in selected)
        # Set warning.
        warning = None
        # Check draft.proposal.requested_count and len(selected) != draft.proposal.requeste....
        if draft.proposal.requested_count and len(selected) != draft.proposal.requested_count:
            # Set destination.
            destination = "YouTube" if draft.proposal.provider == "youtube" else "Spotify"
            # Set warning.
            warning = f"Requested {draft.proposal.requested_count} songs, but only {len(selected)} unique {destination} matches are available. Refine the request before creation."
        # Check draft.proposal.target_duration_ms and abs(duration - draft.proposal.target_....
        if draft.proposal.target_duration_ms and abs(duration - draft.proposal.target_duration_ms) > 30_000:
            # Set warning.
            warning = (warning + " " if warning else "") + "Could not match the requested listening time within 30 seconds using verified whole tracks. Refine the request before creation."
        # Return PlaylistPreview(draft_id=draft_id, proposal=draft.proposal, matches=draft.m....
        return PlaylistPreview(
            draft_id=draft_id, proposal=draft.proposal, matches=draft.matches,
            matched_count=sum(match.status == "matched" for match in draft.matches),
            expires_in=max(0, int(draft.expires_at - time.monotonic())),
            approved=draft.approved, result=draft.result,
            total_duration_ms=duration, constraint_warning=warning,
        )

    # Define approve.
    def approve(self, draft_id: str, token: str) -> None:
        # Set draft.
        draft = self.draft(draft_id, token)
        # Check self.preview(draft_id, token).constraint_warning.
        if self.preview(draft_id, token).constraint_warning:
            # Stop this request with an explicit HTTP error.
            raise HTTPException(status_code=409, detail="The draft does not meet the requested count or duration. Generate another preview instead of creating a shorter playlist.")
        # Check not any((match.status == 'matched' for match in draft.matches)).
        if not any(match.status == "matched" for match in draft.matches):
            # Stop this request with an explicit HTTP error.
            raise HTTPException(status_code=409, detail="No unambiguous tracks matched; nothing to create.")
        # Set draft.approved.
        draft.approved = True

    # Define create as an awaited operation.
    async def create(self, draft_id: str, token: str) -> PlaylistResult:
        # Set draft.
        draft = self.draft(draft_id, token)
        # Manage draft.lock with automatic cleanup.
        async with draft.lock:
            # Check not draft.approved.
            if not draft.approved:
                # Stop this request with an explicit HTTP error.
                raise HTTPException(status_code=403, detail="The user must approve this draft in Playit first.")
            # Check draft.result is not None.
            if draft.result is not None:
                # Do not retry uncertain writes: timeouts may mean Spotify accepted them.
                return draft.result
            # Set tracks.
            tracks = [match.track for match in draft.matches
                      if match.status == "matched" and match.track is not None]
            # Set provider.
            provider = self.providers[draft.proposal.provider]
            # Block automatic retry even when creation has an uncertain outcome.
            draft.result = PlaylistResult(playlist_id="", url="", total=len(tracks), status="needs_review")
            # Wait for the operation and keep playlist_id.
            playlist_id = await provider.create(draft.proposal, token)
            # Set draft.result.
            draft.result = PlaylistResult(
                playlist_id=playlist_id, url=provider.playlist_url(playlist_id), total=len(tracks),
            )
            # Handle failures from this operation below.
            try:
                # Set batch_size.
                batch_size = 1 if draft.proposal.provider == "youtube" else 100
                # Process each start in range(0, len(tracks), batch_size).
                for start in range(0, len(tracks), batch_size):
                    # Set batch.
                    batch = tracks[start:start + batch_size]
                    # Wait for provider.add(playlist_id, batch, token).
                    await provider.add(playlist_id, batch, token)
                    # Update draft.result.added.
                    draft.result.added += len(batch)
            except HTTPException:
                # Set draft.result.status.
                draft.result.status = "needs_review"
                # Propagate this failure instead of continuing.
                raise
            # Set draft.result.status.
            draft.result.status = "complete"
            # Return draft.result.
            return draft.result


# Set playlist_service.
playlist_service = PlaylistService()

# File summary
# - Stores short-lived owner-bound drafts and music sessions in memory.
# - Deduplicates tracks and selects whole songs for duration constraints.
# - Requires approval and records uncertain writes to prevent blind retries.
