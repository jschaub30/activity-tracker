"""Account-level operations (data wipe, etc.)."""

from typing import Type, TypeVar

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, SQLModel, select

from garmin_tracker.deps import CurrentUser, SessionDep
from garmin_tracker.models import Activity, GarminSession, SyncRun, SyncStatus
from garmin_tracker.schemas import DeleteDataOut

router = APIRouter(prefix="/api/account", tags=["account"])

T = TypeVar("T", bound=SQLModel)


def _delete_user_rows(session: Session, model: Type[T], user_id: str) -> int:
    rows = list(session.exec(select(model).where(model.user_id == user_id)).all())  # type: ignore[attr-defined]
    for row in rows:
        session.delete(row)
    return len(rows)


@router.delete("/data", response_model=DeleteDataOut)
def delete_all_data(session: SessionDep, user: CurrentUser) -> DeleteDataOut:
    """Delete activity data for the current user.

    Removes activities and sync history only. Garmin connection credentials and
    share links are left intact. Clears the sync cursor (``last_success_at``)
    so the next sync does a full backfill instead of a short incremental pull.
    """
    running = session.exec(
        select(SyncRun)
        .where(SyncRun.user_id == user.id, SyncRun.status == SyncStatus.running)
        .limit(1)
    ).first()
    if running:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete data while a sync is running. Wait for it to finish.",
        )

    activities = _delete_user_rows(session, Activity, user.id)
    sync_runs = _delete_user_rows(session, SyncRun, user.id)

    # Keep connection tokens, but reset the incremental cursor so the next sync
    # pulls the full backfill window (not only the last few days).
    garmin = session.exec(
        select(GarminSession).where(GarminSession.user_id == user.id)
    ).first()
    if garmin:
        garmin.last_success_at = None
        garmin.last_error = None
        session.add(garmin)

    session.commit()

    return DeleteDataOut(
        activities_deleted=activities,
        sync_runs_deleted=sync_runs,
        message="Activity data deleted. Garmin connection and share links were kept.",
    )
