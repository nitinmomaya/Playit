from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gemini_setup.router import router as gemini_router
from login.router import router as login_router
from spotify.router import router as spotify_router
from music.router import router as music_router
from music.mcp_server import mcp, mcp_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="Playit API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Retry-After"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Playit backend is running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(spotify_router)
app.include_router(login_router)
app.include_router(gemini_router)
app.include_router(music_router)
app.mount("/mcp", mcp_app)
