from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from garmin_tracker.config import get_settings
from garmin_tracker.db import init_db
from garmin_tracker.routers import (
    account,
    activities,
    auth,
    garmin,
    months,
    public,
    share,
    sync,
    weeks,
    years,
)


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

    @app.middleware("http")
    async def origin_secret_gate(request: Request, call_next):
        secret = get_settings().origin_secret
        if secret and request.headers.get("x-origin-secret") != secret:
            return JSONResponse({"detail": "Forbidden"}, status_code=403)
        return await call_next(request)

    app.include_router(auth.router)
    app.include_router(account.router)
    app.include_router(garmin.router)
    app.include_router(sync.router)
    app.include_router(activities.router)
    app.include_router(weeks.router)
    app.include_router(months.router)
    app.include_router(years.router)
    app.include_router(share.router)
    app.include_router(public.router)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "app": settings.app_name}

    return app


app = create_app()
