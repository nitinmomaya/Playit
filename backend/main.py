# Import asynccontextmanager.
from contextlib import asynccontextmanager

# Import FastAPI.
from fastapi import FastAPI
# Import CORSMiddleware.
from fastapi.middleware.cors import CORSMiddleware

# Import gemini_router.
from gemini_setup.router import router as gemini_router
# Import login_router.
from login.router import router as login_router
# Import spotify_router.
from spotify.router import router as spotify_router
# Import music_router.
from music.router import router as music_router
# Import mcp, mcp_app.
from music.mcp_server import mcp, mcp_app
# Import youtube_router.
from youtube.router import router as youtube_router


# Define lifespan as an awaited operation.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Manage mcp.session_manager.run() with automatic cleanup.
    async with mcp.session_manager.run():
        yield


# Set app.
app = FastAPI(title="Playit API", lifespan=lifespan)

# Call app.add_middleware.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Retry-After"],
)


# Define root.
@app.get("/")
def root() -> dict[str, str]:
    # Return the assembled result to the caller.
    return {"message": "Playit backend is running"}


# Define health.
@app.get("/health")
def health() -> dict[str, str]:
    # Return the assembled result to the caller.
    return {"status": "ok"}


# Call app.include_router.
app.include_router(spotify_router)
# Call app.include_router.
app.include_router(login_router)
# Call app.include_router.
app.include_router(gemini_router)
# Call app.include_router.
app.include_router(music_router)
# Call app.include_router.
app.include_router(youtube_router)
# Call app.mount.
app.mount("/mcp", mcp_app)

# File summary
# - Builds the FastAPI application and development CORS policy.
# - Registers OAuth, chat, music routes, and the MCP sub-application.
# - Runs the MCP session manager during application lifetime.
