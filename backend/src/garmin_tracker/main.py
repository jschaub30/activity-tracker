from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from garmin_tracker.config import get_settings
from garmin_tracker.db import init_db
from garmin_tracker.routers import activities, auth, garmin, sync, weeks


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(garmin.router)
    app.include_router(sync.router)
    app.include_router(activities.router)
    app.include_router(weeks.router)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "app": settings.app_name}

    static_path = settings.static_path
    if static_path is not None:
        _mount_spa(app, static_path)

    return app


def _mount_spa(app: FastAPI, static_path: Path) -> None:
    """Serve Vite build: assets/ + SPA fallback for client routes."""
    assets = static_path / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    index = static_path / "index.html"

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        # API routes are registered first; this only catches non-API browser routes
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(status_code=404, detail="Not found")
        candidate = static_path / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)


app = create_app()
