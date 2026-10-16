"""Short-lived, owner-bound drafts. Spotify catalog data never goes to Gemini."""

import asyncio
import hashlib
import secrets
import time
from dataclasses import dataclass, field

from fastapi import HTTPException

from music.models import PlaylistPreview, PlaylistProposal, PlaylistResult, SongMatch
from music.providers import MusicProvider, SpotifyProvider

DRAFT_TTL = 15 * 60
SESSION_TTL = 50 * 60
MAX_ENTRIES = 500


@dataclass
class Draft:
    owner: str
    proposal: PlaylistProposal
    matches: list[SongMatch]
    expires_at: float
    approved: bool = False
    result: PlaylistResult | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class PlaylistService:
    def __init__(self) -> None:
        self.providers: dict[str, MusicProvider] = {"spotify": SpotifyProvider()}
        self.drafts: dict[str, Draft] = {}
        self.sessions: dict[str, tuple[str, float]] = {}

    def prune(self) -> None:
        now = time.monotonic()
        self.drafts = {key: value for key, value in self.drafts.items()
                       if value.expires_at > now or value.lock.locked()}
        self.sessions = {key: value for key, value in self.sessions.items() if value[1] > now}

    def connect(self, token: str) -> str:
        self.prune()
        if len(self.sessions) >= MAX_ENTRIES:
            raise HTTPException(status_code=503, detail="Too many active music sessions.")
        session_id = secrets.token_urlsafe(32)
        self.sessions[session_id] = (token, time.monotonic() + SESSION_TTL)
        return session_id

    def session_token(self, session_id: str) -> str:
        self.prune()
        session = self.sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=401, detail="Music session is invalid or expired.")
        return session[0]

    @staticmethod
    def owner(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def draft(self, draft_id: str, token: str) -> Draft:
        self.prune()
        draft = self.drafts.get(draft_id)
        if draft is None or not secrets.compare_digest(draft.owner, self.owner(token)):
            raise HTTPException(status_code=404, detail="Playlist draft not found or expired.")
        return draft

    async def prepare(self, proposal: PlaylistProposal, token: str) -> PlaylistPreview:
        self.prune()
        if len(self.drafts) >= MAX_ENTRIES:
            raise HTTPException(status_code=503, detail="Too many active playlist drafts.")
        provider = self.providers[proposal.provider]
        matches: list[SongMatch] = []
        seen: set[str] = set()
        # Sequential requests intentionally bound upstream concurrency and propagate 429.
        for song in proposal.songs:
            match = await provider.resolve(song, token)
            if match.track:
                if match.track.id in seen:
                    match.status = "duplicate"
                seen.add(match.track.id)
            matches.append(match)
        if proposal.target_duration_ms:
            # Bounded subset-sum in five-second units; Spotify durations stay
            # server-side. Whole songs cannot generally sum to an exact time.
            target = round(proposal.target_duration_ms / 5000)
            states: dict[tuple[int, int], tuple[int, ...]] = {(0, 0): ()}
            for index, match in enumerate(matches):
                if match.status != "matched" or not match.track or not match.track.duration_ms:
                    continue
                units = max(1, round(match.track.duration_ms / 5000))
                for (total, size), selected in list(states.items()):
                    next_total = total + units
                    if next_total <= target + 120 and (not proposal.requested_count or len(selected) < proposal.requested_count):
                        states.setdefault((next_total, size + 1 if proposal.requested_count else 0), (*selected, index))
            options = [(total, selected) for (total, _), selected in states.items() if selected
                       and (not proposal.requested_count or len(selected) == proposal.requested_count)]
            selected = set(min(options, key=lambda item: abs(item[0] - target))[1]) if options else set()
            for index, match in enumerate(matches):
                if match.status == "matched" and index not in selected:
                    match.status = "not_selected"
        # Recheck after network awaits: concurrent requests must not bypass the cap.
        self.prune()
        if len(self.drafts) >= MAX_ENTRIES:
            raise HTTPException(status_code=503, detail="Too many active playlist drafts.")
        draft_id = secrets.token_urlsafe(24)
        self.drafts[draft_id] = Draft(self.owner(token), proposal, matches, time.monotonic() + DRAFT_TTL)
        return self.preview(draft_id, token)

    def preview(self, draft_id: str, token: str) -> PlaylistPreview:
        draft = self.draft(draft_id, token)
        selected = [match.track for match in draft.matches if match.status == "matched" and match.track]
        duration = sum(track.duration_ms or 0 for track in selected)
        warning = None
        if draft.proposal.requested_count and len(selected) != draft.proposal.requested_count:
            warning = f"Requested {draft.proposal.requested_count} songs, but only {len(selected)} unique Spotify matches are available. Refine the request before creation."
        if draft.proposal.target_duration_ms and abs(duration - draft.proposal.target_duration_ms) > 30_000:
            warning = (warning + " " if warning else "") + "Could not match the requested listening time within 30 seconds using verified whole tracks. Refine the request before creation."
        return PlaylistPreview(
            draft_id=draft_id, proposal=draft.proposal, matches=draft.matches,
            matched_count=sum(match.status == "matched" for match in draft.matches),
            expires_in=max(0, int(draft.expires_at - time.monotonic())),
            approved=draft.approved, result=draft.result,
            total_duration_ms=duration, constraint_warning=warning,
        )

    def approve(self, draft_id: str, token: str) -> None:
        draft = self.draft(draft_id, token)
        if self.preview(draft_id, token).constraint_warning:
            raise HTTPException(status_code=409, detail="The draft does not meet the requested count or duration. Generate another preview instead of creating a shorter playlist.")
        if not any(match.status == "matched" for match in draft.matches):
            raise HTTPException(status_code=409, detail="No unambiguous tracks matched; nothing to create.")
        draft.approved = True

    async def create(self, draft_id: str, token: str) -> PlaylistResult:
        draft = self.draft(draft_id, token)
        async with draft.lock:
            if not draft.approved:
                raise HTTPException(status_code=403, detail="The user must approve this draft in Playit first.")
            if draft.result is not None:
                # Do not retry uncertain writes: timeouts may mean Spotify accepted them.
                return draft.result
            tracks = [match.track for match in draft.matches
                      if match.status == "matched" and match.track is not None]
            provider = self.providers[draft.proposal.provider]
            # Block automatic retry even when creation has an uncertain outcome.
            draft.result = PlaylistResult(playlist_id="", url="", total=len(tracks), status="needs_review")
            playlist_id = await provider.create(draft.proposal, token)
            draft.result = PlaylistResult(
                playlist_id=playlist_id, url=provider.playlist_url(playlist_id), total=len(tracks),
            )
            try:
                for start in range(0, len(tracks), 100):
                    batch = tracks[start:start + 100]
                    await provider.add(playlist_id, batch, token)
                    draft.result.added += len(batch)
            except HTTPException:
                draft.result.status = "needs_review"
                raise
            draft.result.status = "complete"
            return draft.result


playlist_service = PlaylistService()