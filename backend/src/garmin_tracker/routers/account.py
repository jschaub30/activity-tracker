"""Account-level operations (data wipe, etc.)."""

from fastapi import APIRouter, HTTPException

from garmin_tracker.deps import CurrentUser
from garmin_tracker.schemas import DeleteDataOut
from garmin_tracker.services.sync_service import STALE_SYNC_SECONDS
from garmin_tracker.store import repo

router = APIRouter(prefix="/api/account", tags=["account"])


@router.delete("/data", response_model=DeleteDataOut)
def delete_all_data(user: CurrentUser) -> DeleteDataOut:
    """Delete activity data for the current user.

    Removes activities and sync history only. Garmin connection credentials and
    share links are left intact. Clears the sync cursor (``last_success_at``)
    so the next sync does a full backfill instead of a short incremental pull.
    """
    if repo.is_sync_running(user.id, stale_after_seconds=STALE_SYNC_SECONDS):
        raise HTTPException(
            status_code=409,
            detail="Cannot delete data while a sync is running. Wait for it to finish.",
        )

    activities, sync_runs = repo.wipe_activity_data(user.id)
    return DeleteDataOut(
        activities_deleted=activities,
        sync_runs_deleted=sync_runs,
        message="Activity data deleted. Garmin connection and share links were kept.",
    )
