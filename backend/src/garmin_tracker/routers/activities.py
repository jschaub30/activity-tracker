from fastapi import APIRouter, HTTPException

from garmin_tracker.deps import CurrentUser
from garmin_tracker.models import utcnow
from garmin_tracker.schemas import ActivityOut, ActivityUpdate
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
    act.updated_at = utcnow()
    repo.put_activity(act)
    rebuild_weeks_for_times(user, [act.start_time])
    return _to_out(act)
