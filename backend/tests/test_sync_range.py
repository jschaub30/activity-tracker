from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from garmin_tracker.config import get_settings
from garmin_tracker.models import (
    Activity,
    ActivityCategory,
    GarminSession,
    ReviewStatus,
    User,
)
from garmin_tracker.services.sync_service import INCREMENTAL_OVERLAP_DAYS, SyncService
from garmin_tracker.store import repo


def _user_with_garmin(*, last_success_at: datetime | None) -> str:
    user_id = str(uuid4())
    repo.create_user(
        User(
            id=user_id,
            email=f"range-{uuid4().hex}@example.com",
            password_hash="x",
        )
    )
    repo.put_garmin(
        GarminSession(
            user_id=user_id,
            encrypted_token="token",
            garmin_email="g@example.com",
            last_success_at=last_success_at,
        )
    )
    return user_id


def test_compute_range_full_backfill_when_no_activities():
    last = datetime.now(UTC)
    user_id = _user_with_garmin(last_success_at=last)
    user = repo.get_user(user_id)
    assert user is not None
    garmin = SyncService(user).garmin_row()
    assert garmin is not None
    start, end = SyncService(user)._compute_range(garmin)

    today = datetime.now(UTC).date()
    assert end == today
    assert start == today - timedelta(days=get_settings().backfill_days)


def test_compute_range_incremental_when_activities_exist():
    last = datetime.now(UTC)
    user_id = _user_with_garmin(last_success_at=last)
    repo.put_activity(
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
    user = repo.get_user(user_id)
    assert user is not None
    garmin = SyncService(user).garmin_row()
    assert garmin is not None
    start, end = SyncService(user)._compute_range(garmin)

    today = datetime.now(UTC).date()
    expected_start = (last - timedelta(days=INCREMENTAL_OVERLAP_DAYS)).date()
    assert end == today
    assert start == expected_start
    assert (end - start).days <= INCREMENTAL_OVERLAP_DAYS + 1


def test_compute_range_full_backfill_without_last_success():
    user_id = _user_with_garmin(last_success_at=None)
    user = repo.get_user(user_id)
    assert user is not None
    garmin = SyncService(user).garmin_row()
    assert garmin is not None
    start, end = SyncService(user)._compute_range(garmin)

    today = date.today()
    assert abs((end - today).days) <= 1
    assert (end - start).days == get_settings().backfill_days
