from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from garmin_tracker.models import (
    Activity,
    ActivityCategory,
    GarminSession,
    ReviewStatus,
    SyncRun,
    SyncStatus,
    User,
)
from garmin_tracker.services.sync_service import (
    HISTORY_START,
    INCREMENTAL_OVERLAP_DAYS,
    STALE_SYNC_SECONDS,
    SyncService,
)
from garmin_tracker.store import repo


def _user_with_garmin(
    *,
    last_success_at: datetime | None,
    history_complete: bool = False,
) -> str:
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
            history_complete=history_complete,
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
    assert start == HISTORY_START


def test_compute_range_incremental_when_activities_exist():
    last = datetime.now(UTC)
    user_id = _user_with_garmin(last_success_at=last, history_complete=True)
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
    assert start == HISTORY_START


def test_compute_range_full_history_until_complete():
    last = datetime.now(UTC)
    user_id = _user_with_garmin(last_success_at=last, history_complete=False)
    repo.put_activity(
        Activity(
            user_id=user_id,
            garmin_activity_id="1",
            name="Run",
            start_time=last,
            category=ActivityCategory.run,
            suggested_category=ActivityCategory.run,
        )
    )
    user = repo.get_user(user_id)
    assert user is not None
    garmin = SyncService(user).garmin_row()
    assert garmin is not None
    start, _end = SyncService(user)._compute_range(garmin)
    assert start == HISTORY_START


def test_begin_sync_rejects_fresh_running_run():
    user_id = _user_with_garmin(last_success_at=None)
    user = repo.get_user(user_id)
    assert user is not None
    run = SyncService(user).create_running_sync()
    assert run.status == SyncStatus.running
    try:
        SyncService(user).begin_sync()
        raise AssertionError("expected already-running error")
    except RuntimeError as exc:
        assert "already running" in str(exc)


def test_begin_sync_resumes_stale_running_run():
    user_id = _user_with_garmin(last_success_at=None)
    user = repo.get_user(user_id)
    assert user is not None
    stale = SyncRun(
        user_id=user_id,
        status=SyncStatus.running,
        cursor="2026-04-19",
        started_at=datetime.now(UTC) - timedelta(seconds=STALE_SYNC_SECONDS + 30),
        updated_at=datetime.now(UTC) - timedelta(seconds=STALE_SYNC_SECONDS + 30),
    )
    repo.put_sync_run(stale)
    resumed = SyncService(user).begin_sync()
    assert resumed.id == stale.id
    assert resumed.cursor == "2026-04-19"
    assert resumed.status == SyncStatus.running
