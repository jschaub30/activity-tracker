from fastapi import APIRouter, HTTPException, Query

from garmin_tracker.deps import CurrentUser
from garmin_tracker.models import ReviewStatus, utcnow
from garmin_tracker.schemas import (
    ActivityOut,
    ActivityUpdate,
    BulkConfirmRequest,
)
from garmin_tracker.services.week_service import rebuild_weeks_for_times
from garmin_tracker.store import repo
from garmin_tracker.units import m_to_ft, m_to_mi

router = APIRouter(prefix="/api/activities", tags=["activities"])


def _to_out(act) -> ActivityOut:
    data = ActivityOut.model_validate(act)
    data.distance_mi = m_to_mi(act.distance_m)
    data.elevation_ft = m_to_ft(act.elevation_gain_m)
    if data.calories is None and act.active_calories is not None:
        data.calories = act.active_calories
    return data


@router.get("/review", response_model=list[ActivityOut])
def list_review_queue(
    user: CurrentUser,
    limit: int = Query(default=100, le=500),
) -> list[ActivityOut]:
    return [_to_out(a) for a in repo.list_pending(user.id, limit=limit)]


@router.get("/{activity_id}", response_model=ActivityOut)
def get_activity(activity_id: str, user: CurrentUser) -> ActivityOut:
    act = repo.get_activity(user.id, activity_id)
    if not act:
        raise HTTPException(status_code=404, detail="Activity not found")
    return _to_out(act)


@router.patch("/{activity_id}", response_model=ActivityOut)
def update_activity(
    activity_id: str,
    body: ActivityUpdate,
    user: CurrentUser,
) -> ActivityOut:
    act = repo.get_activity(user.id, activity_id)
    if not act:
        raise HTTPException(status_code=404, detail="Activity not found")

    if body.category is not None:
        act.category = body.category
    if body.review_status is not None:
        act.review_status = body.review_status
    if body.category is not None and body.review_status is None:
        act.review_status = ReviewStatus.confirmed

    act.updated_at = utcnow()
    repo.put_activity(act)
    if act.review_status == ReviewStatus.confirmed:
        rebuild_weeks_for_times(user, [act.start_time])
    return _to_out(act)


@router.post("/bulk-confirm", response_model=dict)
def bulk_confirm(body: BulkConfirmRequest, user: CurrentUser) -> dict:
    pending = repo.list_pending(user.id, limit=500)
    if body.activity_ids is not None:
        wanted = set(body.activity_ids)
        pending = [a for a in pending if a.id in wanted]
    count = 0
    times = []
    for act in pending:
        if body.accept_suggested:
            act.category = act.suggested_category
        act.review_status = ReviewStatus.confirmed
        act.updated_at = utcnow()
        repo.put_activity(act)
        times.append(act.start_time)
        count += 1
    if times:
        rebuild_weeks_for_times(user, times)
    return {"confirmed": count}
