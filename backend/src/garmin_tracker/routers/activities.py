from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from garmin_tracker.deps import CurrentUser, SessionDep
from garmin_tracker.models import Activity, ReviewStatus, utcnow
from garmin_tracker.schemas import (
    ActivityOut,
    ActivityUpdate,
    BulkConfirmRequest,
)
from garmin_tracker.units import m_to_ft, m_to_mi

router = APIRouter(prefix="/api/activities", tags=["activities"])


def _to_out(act: Activity) -> ActivityOut:
    data = ActivityOut.model_validate(act)
    data.distance_mi = m_to_mi(act.distance_m)
    data.elevation_ft = m_to_ft(act.elevation_gain_m)
    # Prefer Garmin "calories"; fall back to active_calories for older rows
    if data.calories is None and act.active_calories is not None:
        data.calories = act.active_calories
    return data


@router.get("/review", response_model=list[ActivityOut])
def list_review_queue(
    session: SessionDep,
    user: CurrentUser,
    limit: int = Query(default=100, le=500),
) -> list[ActivityOut]:
    stmt = (
        select(Activity)
        .where(Activity.user_id == user.id, Activity.review_status == ReviewStatus.pending)
        .order_by(Activity.start_time.desc())  # type: ignore[attr-defined]
        .limit(limit)
    )
    return [_to_out(a) for a in session.exec(stmt).all()]


@router.get("/{activity_id}", response_model=ActivityOut)
def get_activity(activity_id: str, session: SessionDep, user: CurrentUser) -> ActivityOut:
    act = session.get(Activity, activity_id)
    if not act or act.user_id != user.id:
        raise HTTPException(status_code=404, detail="Activity not found")
    return _to_out(act)


@router.patch("/{activity_id}", response_model=ActivityOut)
def update_activity(
    activity_id: str,
    body: ActivityUpdate,
    session: SessionDep,
    user: CurrentUser,
) -> ActivityOut:
    act = session.get(Activity, activity_id)
    if not act or act.user_id != user.id:
        raise HTTPException(status_code=404, detail="Activity not found")

    if body.category is not None:
        act.category = body.category
    if body.review_status is not None:
        act.review_status = body.review_status
    # Confirming without explicit status when category set is common UX
    if body.category is not None and body.review_status is None:
        act.review_status = ReviewStatus.confirmed

    act.updated_at = utcnow()
    session.add(act)
    session.commit()
    session.refresh(act)
    return _to_out(act)


@router.post("/bulk-confirm", response_model=dict)
def bulk_confirm(
    body: BulkConfirmRequest,
    session: SessionDep,
    user: CurrentUser,
) -> dict:
    stmt = select(Activity).where(
        Activity.user_id == user.id,
        Activity.review_status == ReviewStatus.pending,
    )
    if body.activity_ids is not None:
        stmt = stmt.where(Activity.id.in_(body.activity_ids))  # type: ignore[attr-defined]

    rows = list(session.exec(stmt).all())
    count = 0
    for act in rows:
        if body.accept_suggested:
            act.category = act.suggested_category
        act.review_status = ReviewStatus.confirmed
        act.updated_at = utcnow()
        session.add(act)
        count += 1
    session.commit()
    return {"confirmed": count}
