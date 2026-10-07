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
python -m pip install "fastapi[standard]"
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
