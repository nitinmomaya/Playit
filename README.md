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
