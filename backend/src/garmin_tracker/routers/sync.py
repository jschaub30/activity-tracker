from fastapi import APIRouter, BackgroundTasks, HTTPException
from sqlmodel import Session

from garmin_tracker.db import engine
from garmin_tracker.deps import CurrentUser, SessionDep
from garmin_tracker.models import User
from garmin_tracker.schemas import SyncStartOut, SyncStatusOut
from garmin_tracker.services.sync_service import SyncService

router = APIRouter(prefix="/api/sync", tags=["sync"])


def _run_sync_job(user_id: str, run_id: str) -> None:
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            return
        SyncService(session, user).execute_sync(run_id)


@router.post("", response_model=SyncStartOut)
def start_sync(
    session: SessionDep,
    user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> SyncStartOut:
    svc = SyncService(session, user)
    try:
        run = svc.create_running_sync()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    background_tasks.add_task(_run_sync_job, user.id, run.id)
    return SyncStartOut(
        message="Sync started — activities will appear in Review when finished.",
        sync_run_id=run.id,
    )


@router.get("/status", response_model=SyncStatusOut)
def sync_status(session: SessionDep, user: CurrentUser) -> SyncStatusOut:
    svc = SyncService(session, user)
    run = svc.latest_run()
    if not run:
        return SyncStatusOut(is_running=False)
    return SyncStatusOut(
        id=run.id,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        activities_fetched=run.activities_fetched,
        activities_created=run.activities_created,
        activities_updated=run.activities_updated,
        error=run.error,
        is_running=svc.is_running(),
    )
