from datetime import UTC, datetime
from uuid import uuid4

from garmin_tracker.models import (
    Activity,
    ActivityCategory,
    ReviewStatus,
    User,
)
from garmin_tracker.store import repo


def test_email_uniqueness():
    email = f"uniq-{uuid4().hex}@example.com"
    repo.create_user(User(id=str(uuid4()), email=email, password_hash="x"))
    try:
        repo.create_user(User(id=str(uuid4()), email=email, password_hash="y"))
        raise AssertionError("expected duplicate email to fail")
    except ValueError:
        pass


def test_upsert_by_garmin_id_preserves_confirmed_category():
    user_id = str(uuid4())
    repo.create_user(
        User(id=user_id, email=f"{user_id}@example.com", password_hash="x")
    )
    start = datetime(2026, 3, 1, 12, tzinfo=UTC)
    first = Activity(
        user_id=user_id,
        garmin_activity_id="g-1",
        name="Run",
        start_time=start,
        category=ActivityCategory.hike,
        suggested_category=ActivityCategory.run,
        review_status=ReviewStatus.confirmed,
        distance_m=1000,
    )
    repo.put_activity(first)
    existing = repo.get_activity_by_garmin_id(user_id, "g-1")
    assert existing is not None
    existing.name = "Run updated"
    existing.distance_m = 2000
    repo.put_activity(existing)
    again = repo.get_activity_by_garmin_id(user_id, "g-1")
    assert again is not None
    assert again.id == first.id
    assert again.category == ActivityCategory.hike
    assert again.distance_m == 2000


def test_pending_review_order():
    user_id = str(uuid4())
    repo.create_user(
        User(id=user_id, email=f"{user_id}@example.com", password_hash="x")
    )
    older = datetime(2026, 1, 1, tzinfo=UTC)
    newer = datetime(2026, 2, 1, tzinfo=UTC)
    repo.put_activity(
        Activity(
            user_id=user_id,
            garmin_activity_id="old",
            name="Old",
            start_time=older,
            review_status=ReviewStatus.pending,
        )
    )
    repo.put_activity(
        Activity(
            user_id=user_id,
            garmin_activity_id="new",
            name="New",
            start_time=newer,
            review_status=ReviewStatus.pending,
        )
    )
    repo.put_activity(
        Activity(
            user_id=user_id,
            garmin_activity_id="done",
            name="Done",
            start_time=newer,
            review_status=ReviewStatus.confirmed,
        )
    )
    pending = repo.list_pending(user_id)
    assert [a.garmin_activity_id for a in pending] == ["new", "old"]
