"""SolarSense API: serves precomputed results as JSON and the dashboard website.

Start it from the solarsense folder with:   uvicorn api.main:app --reload
Then open http://localhost:8000 (dashboard) or http://localhost:8000/docs (try the API).
"""

import mimetypes
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api import auth
from api.data_store import get_store
from api.routes import alerts, chat, plants, replay, reports, weather
from engine import config
from engine.create_users import ensure_demo_users


@asynccontextmanager
async def lifespan(app):
    """Load every data file once when the server starts (so each request is fast)."""
    ensure_demo_users()   # first run / fresh server: create the DEMO accounts so login works
    get_store()
    yield


app = FastAPI(title="SolarSense API", description="AI solar plant health monitor — precomputed results.",
              version="1.0", lifespan=lifespan)

# CORS lets a page opened from another address (e.g. a local test file) call this API.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
# Login guard: every page and API call needs a logged-in user (except the login page itself).
app.middleware("http")(auth.require_login)

app.include_router(auth.router)
app.include_router(plants.router)
app.include_router(alerts.router)
app.include_router(reports.router)
app.include_router(replay.router)
app.include_router(weather.router)
app.include_router(chat.router)


@app.get("/api/health", tags=["health"])
def health():
    """Simple check that the server is up."""
    return {"status": "ok"}


# Charts made by the pipeline (e.g. the injected-fault example), read-only.
config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/figures", StaticFiles(directory=config.FIGURES_DIR), name="figures")

# Browsers only accept the app manifest (installable app) with this file type.
mimetypes.add_type("application/manifest+json", ".webmanifest")

# The website. Mounted LAST so it never hides the /api routes above.
app.mount("/", StaticFiles(directory=config.WEB_DIR, html=True), name="web")
