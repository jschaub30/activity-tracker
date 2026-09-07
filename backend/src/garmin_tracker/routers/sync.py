from fastapi import APIRouter, BackgroundTasks, HTTPException

from garmin_tracker.config import get_settings
from garmin_tracker.deps import CurrentUser
from garmin_tracker.schemas import SyncStartOut, SyncStatusOut
from garmin_tracker.services.sync_service import SyncService, enqueue_sync, run_sync_job

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("", response_model=SyncStartOut)
def start_sync(user: CurrentUser, background_tasks: BackgroundTasks) -> SyncStartOut:
    svc = SyncService(user)
    try:
        run = svc.create_running_sync()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if (get_settings().sync_backend or "inline").lower() == "sqs":
        enqueue_sync(user.id, run.id)
    else:
        background_tasks.add_task(run_sync_job, user.id, run.id)
    return SyncStartOut(
        message="Sync started — activities will appear in Review when finished.",
        sync_run_id=run.id,
    )


@router.get("/status", response_model=SyncStatusOut)
def sync_status(user: CurrentUser) -> SyncStatusOut:
    svc = SyncService(user)
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
