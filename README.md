# Playit

Playit is a playlist of songs recommended by AI for YouTube Music and Spotify.

## Tech stack

### Frontend

- **React 19** — builds the interactive user interface.
- **TypeScript** — adds static typing to JavaScript.
- **Vite** — runs the local development server and builds the frontend.

### Backend

- **Python** — backend programming language.
- **FastAPI** — defines the HTTP API and provides automatic API documentation.
- **Uvicorn** — serves the FastAPI application locally.

The frontend development server is allowed to call the backend at `localhost:8000` through FastAPI's CORS configuration.

## Run locally

Run the frontend and backend in separate terminal windows.

### Backend

From the project root, create and activate a virtual environment, then install the backend packages:

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Start the API server (keep the virtual environment activated):

```sh
python -m uvicorn main:app --reload
```

The API runs at <http://127.0.0.1:8000>. Interactive API documentation is at <http://127.0.0.1:8000/docs>.

To start it again in a new terminal, run `cd backend`, `source .venv/bin/activate`, and then the Uvicorn command above.

### Frontend

In a second terminal, from the project root:

```sh
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite (normally <http://localhost:5173>). `npm install` is only needed the first time or after frontend dependencies change.

## Spotify backend API

All Spotify HTTP API requests go through the backend. Spotify's authorization
screen is still opened in the browser via `GET /login` (OAuth requires this).
Keep `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, and `SPOTIFY_REDIRECT_URI`
in the backend environment. The redirect URI must exactly match the one registered
in the Spotify dashboard and point to the backend `/callback`.

Optional settings: `FRONTEND_CALLBACK_URL` (default
`http://localhost:5173/auth/callback`) and `VITE_API_BASE_URL` (default
`http://localhost:8000`). Use the same backend hostname for login and API requests
so that OAuth state cookies are available. Add production frontend origins to CORS
before deployment.

| Backend route | Request | Response |
| --- | --- | --- |
| `POST /spotify/token` | JSON: `grant_type: "authorization_code"`, `code`, `state`; requires the state cookie created by `/login` | Spotify token fields: `access_token`, `refresh_token`, `token_type`, `expires_in`, `scope` |
| `POST /spotify/token` | JSON: `grant_type: "refresh_token"`, `refresh_token` | New token fields; preserves the existing refresh token if Spotify does not rotate it |
| `GET /spotify/me` | `Authorization: Bearer <access_token>` | Spotify current-user profile |
| `GET /spotify/users/{user_id}/playlists` | `Authorization: Bearer <access_token>` | `{ "items": [...], "total": number }`, aggregating all available pages |

The existing `/callback` exchanges the authorization code server-side using the
same token service. It sends tokens to the frontend in a URL fragment (not a query
string); the frontend stores them in memory, clears the fragment, and fetches the
profile from `/spotify/me`. Refresh tokens are sent only to the token route, not
on every API request. After using the frontend `refreshSpotifyToken()` helper,
save the returned tokens with `setAuth()` (convert `expires_in` to a string).
Automatic refresh/retry and server-side token sessions are not implemented.

Playlist visibility depends on Spotify permissions: `playlist-read-private` and
`playlist-read-collaborative` are requested during login. The user-ID playlist
endpoint is deprecated by Spotify and may be restricted for some apps; upstream
401/403/429 responses are preserved, including the `Retry-After` header on 429.
The API never exposes the client secret.

Spotify HTTPS requests use `truststore` to verify certificates against the OS
certificate store, including trusted enterprise CAs on macOS. TLS verification
remains enabled. Custom CA bundles can also be provided via `SSL_CERT_FILE` or
`SSL_CERT_DIR`.

Backend tests use mocked Spotify requests and require no Spotify credentials:
run `python -m unittest discover -s tests -v` from the backend directory.

## YouTube backend API

This integration uses **Google OAuth and the official YouTube Data API v3**,
not an unofficial YouTube Music API. It mirrors Spotify's structure:

- `backend/youtube/router.py`: HTTP routes, bearer authentication, query validation.
- `backend/youtube/service.py`: Google login redirect, state/PKCE cookies, callback.
- `backend/youtube/web_api.py`: request models, token exchange/refresh, upstream API calls.

### Google Cloud setup

1. Enable **YouTube Data API v3** in the project containing your OAuth client.
2. Use a **Web application** OAuth client. Register the exact backend redirect
	URI, e.g. `http://127.0.0.1:8000/youtube/callback`.
3. Configure the consent screen and add your account as a test user while the
	app is External / Testing.
4. Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `YOUTUBE_REDIRECT_URI`
	in the backend environment (or the existing root `.env`). Never put the
	secret in a frontend `VITE_` variable or commit credentials.

Login requests `openid email profile` and
`https://www.googleapis.com/auth/youtube.force-ssl`, supporting playlist reads
and writes. Existing read-only authorizations must reconnect and grant the new
scope; refreshing an old token cannot add permission. Add this scope in Google
Auth Platform's Data Access configuration. Login explicitly prompts for account
selection and consent.

Both providers now land on the same chat/sidebar UI after login. YouTube login
only fetches the Google profile, not channels or playlists. YouTube chat supports
Agent and REST modes through the shared draft workflow. The selected provider
chooses the matching adapter and bearer token. Playlist requests produce a preview
and an **Approve and create on YouTube** button. Only approving creates a playlist.

YouTube matching uses one bounded search and one video-metadata lookup per song,
with no query retries or pagination. Search consumes API quota; large requests may
hit project limits. Titles and uploaders are heuristic evidence, not verified
artist/recording credits. Alternate editions are skipped; tied best matches select
the first result in YouTube search order, consistent with Spotify's first-best policy;
inspect the real titles/uploaders in the preview. Count/duration constraints can
block creation when too few usable videos are found. Only model recommendations
enter Gemini history, never catalog results or credentials. Draft ownership,
expiry, approval, and uncertain-write guards are shared with Spotify. YouTube
insertions are counted individually; failed writes are not automatically retried.

### Routes and manual verification

| Backend route | Request | Response |
| --- | --- | --- |
| `GET /youtube/login` | Open in a browser | Redirects to Google; sets 10-minute HttpOnly state/PKCE cookies |
| `GET /youtube/callback` | Google supplies `code` and `state`; same browser cookies required | Redirects to the YouTube frontend callback with token fields in a fragment; clears OAuth cookies |
| `POST /youtube/token` | JSON: `grant_type: "authorization_code"`, `code`, `state`; login cookies required | Exchanges code using the server-held PKCE verifier |
| `POST /youtube/token` | JSON: `grant_type: "refresh_token"`, `refresh_token` | New token fields; retains supplied refresh token if Google omits it |
| `GET /youtube/me` | `Authorization: Bearer <google_access_token>` | Google profile (`sub`, name, email, etc., subject to granted scopes) |
| `GET /youtube/channels` | Google bearer; optional `page_token`, `max_results` (1–50) | Native YouTube channel page for `mine=true` |
| `GET /youtube/playlists` | Google bearer; optional `page_token`, `max_results` (1–50) | Native YouTube playlist page for `mine=true` |
| `POST /youtube/create_playlist` | Google bearer; JSON `name`, optional `description`, `privacy_status` (`private` default, `unlisted`, `public`) | 201, created playlist |
| `PUT /youtube/update_playlist/{playlist_id}` | Google bearer; JSON `name`, optional `description` (defaults empty), optional `privacy_status` | Updated playlist; replaces title/description and preserves privacy when omitted |
| `DELETE /youtube/delete_playlist/{playlist_id}` | Google bearer | 204, permanently deletes the playlist |
| `POST /youtube/add_item/{playlist_id}/items` | Google bearer; JSON `video_id`, optional zero-based `position` | 201, inserted playlist item; save its `id` for removal |
| `DELETE /youtube/remove_item/{playlist_item_id}/items` | Google bearer; playlist-item ID, **not** video ID | 204, removes one playlist item |
| `GET /youtube/health` | None | Local route health, not a Google credential/API check |

These are official YouTube video playlists, not a dedicated YouTube Music API.
Writes require a usable YouTube channel and adequate granted permissions. Direct
API callers must obtain user confirmation before writes, especially deletion.
The model is not given these write tools. Each insertion adds one video (not a
Spotify-style batch), and writes are never automatically retried after timeouts.

Start with **Login with YouTube** on the frontend. After consent the backend
redirects to `http://localhost:5173/auth/youtube/callback`. Override this with
`YOUTUBE_FRONTEND_CALLBACK_URL` for another frontend origin. The Google Console
redirect URI remains the backend `YOUTUBE_REDIRECT_URI`, not the frontend URL.
The frontend removes the fragment immediately, loads `/youtube/me`, and stores
Google tokens separately from Spotify in memory. Reloading clears authentication.
Do not use Spotify tokens for YouTube routes.
Use the same backend hostname throughout login so cookies survive the callback.
The callback already consumes the code; do not exchange that code again via
`/youtube/token`.

Collection routes return one page to bound quota usage. Pass the returned
`nextPageToken` as `page_token` for the next page. An empty channel list means
there is no channel available to this authorization; Google profile sign-in
does not guarantee a usable YouTube channel. `/youtube/me` fetches profile data;
it does not validate an ID token or establish a persistent Playit identity.

Offline access is requested, but Google may omit a refresh token on subsequent
logins. Retain a previously stored token; reconnect with explicit re-consent
when necessary. External apps in Testing receive seven-day refresh tokens for
YouTube scopes. Check returned `scope` values: users may deny individual
permissions, in which case dependent API calls may fail with 403. Public
distribution may require Google's OAuth verification.

There is no persisted user session/token database or automatic refresh yet,
matching the existing backend's explicit bearer/token API pattern. Tokens are
returned in non-cacheable token response bodies and in the callback fragment,
following Spotify's existing development pattern. The frontend exposes an explicit
refresh helper when a refresh token exists; automatic retry is not implemented.
A new authorization without a refresh token does not reuse a previous account's
refresh token. Before production deployment, prefer encrypted server-side refresh
token storage and an opaque HttpOnly session cookie. Use HTTPS in production;
never log tokens or send them to the AI. HTTP status codes and 429 Retry-After
are preserved where appropriate, while upstream error details are sanitized.

No additional test cases are included for the YouTube integration.
