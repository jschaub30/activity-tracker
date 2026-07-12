from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from sqlmodel import Session

from garmin_tracker.config import get_settings
from garmin_tracker.db import engine
from garmin_tracker.models import (
    Activity,
    ActivityCategory,
    GarminSession,
    ReviewStatus,
    User,
)
from garmin_tracker.services.sync_service import INCREMENTAL_OVERLAP_DAYS, SyncService


def _user_with_garmin(*, last_success_at: datetime | None) -> tuple[str, str]:
    user_id = str(uuid4())
    with Session(engine) as session:
        session.add(
            User(
                id=user_id,
                email=f"range-{uuid4().hex}@example.com",
                password_hash="x",
            )
        )
        session.add(
            GarminSession(
                user_id=user_id,
                encrypted_token="token",
                garmin_email="g@example.com",
                last_success_at=last_success_at,
            )
        )
        session.commit()
    return user_id


def test_compute_range_full_backfill_when_no_activities():
    """After wipe (or first connect), range is full backfill even if last_success_at is set."""
    last = datetime.now(timezone.utc)
    user_id = _user_with_garmin(last_success_at=last)

    with Session(engine) as session:
        user = session.get(User, user_id)
        assert user is not None
        garmin = SyncService(session, user).garmin_row()
        assert garmin is not None
        start, end = SyncService(session, user)._compute_range(garmin)

    today = datetime.now(timezone.utc).date()
    assert end == today
    assert start == today - timedelta(days=get_settings().backfill_days)


def test_compute_range_incremental_when_activities_exist():
    last = datetime.now(timezone.utc)
    user_id = _user_with_garmin(last_success_at=last)

    with Session(engine) as session:
        session.add(
            Activity(
                user_id=user_id,
                garmin_activity_id="1",
                name="Run",
                start_time=last,
                garmin_type="running",
                suggested_category=ActivityCategory.run,
                category=ActivityCategory.run,
                review_status=ReviewStatus.confirmed,
            )
        )
        session.commit()
        user = session.get(User, user_id)
        assert user is not None
        garmin = SyncService(session, user).garmin_row()
        assert garmin is not None
        start, end = SyncService(session, user)._compute_range(garmin)

    today = datetime.now(timezone.utc).date()
    expected_start = (last - timedelta(days=INCREMENTAL_OVERLAP_DAYS)).date()
    assert end == today
    assert start == expected_start
    # Incremental window is a few days, not a full year
    assert (end - start).days <= INCREMENTAL_OVERLAP_DAYS + 1


def test_compute_range_full_backfill_without_last_success():
    user_id = _user_with_garmin(last_success_at=None)

    with Session(engine) as session:
        user = session.get(User, user_id)
        assert user is not None
        garmin = SyncService(session, user).garmin_row()
        assert garmin is not None
        start, end = SyncService(session, user)._compute_range(garmin)

    today = date.today()
    # allow UTC vs local day boundary of 1 day
    assert abs((end - today).days) <= 1
    assert (end - start).days == get_settings().backfill_days
