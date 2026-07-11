from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

    return app


app = create_app()
