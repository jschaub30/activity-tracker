from datetime import UTC, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from garmin_tracker.models import Activity, ActivityCategory, User
from garmin_tracker.services.period_service import build_months_list, build_years_list
from garmin_tracker.store import repo


def _user() -> User:
    user = User(
        id=str(uuid4()),
        email=f"p-{uuid4().hex}@example.com",
        password_hash="x",
        timezone="America/Denver",
    )
    repo.create_user(user)
    return user


def _act(
    user_id: str,
    garmin_id: str,
    local_iso: str,
    *,
    category: ActivityCategory = ActivityCategory.run,
    distance_m: float = 1609.344,
    elevation_m: float = 30.48,
    calories: float = 100,
) -> None:
    tz = ZoneInfo("America/Denver")
    local = datetime.fromisoformat(local_iso).replace(tzinfo=tz)
    repo.put_activity(
        Activity(
            user_id=user_id,
            garmin_activity_id=garmin_id,
            name=garmin_id,
            start_time=local.astimezone(UTC),
            category=category,
            suggested_category=category,
            distance_m=distance_m,
            elevation_gain_m=elevation_m,
            calories=calories,
        )
    )


def test_years_ytd_is_first_row():
    user = _user()
    now = datetime.now(ZoneInfo("America/Denver"))
    _act(user.id, "old", "2024-06-15T10:00:00")
    ytd = now.replace(hour=10, minute=0, second=0, microsecond=0)
    _act(user.id, "ytd", ytd.strftime("%Y-%m-%dT%H:%M:%S"))
    result = build_years_list(user)
    assert result.years[0].is_ytd is True
    assert result.years[0].label == "YTD"
    assert result.years[0].year == now.year
    years = [y.year for y in result.years]
    assert years[0] == now.year
    assert 2024 in years
    assert years == list(range(now.year, 2023, -1))


def test_years_month_buckets_and_totals():
    user = _user()
    _act(user.id, "jan", "2025-01-10T09:00:00", calories=50)
    _act(
        user.id,
        "strength",
        "2025-01-11T09:00:00",
        category=ActivityCategory.strength,
        distance_m=5000,
        calories=200,
    )
    result = build_years_list(user)
    y2025 = next(y for y in result.years if y.year == 2025)
    jan = y2025.months[0]
    assert jan.month == 1
    assert abs(jan.totals.distance_mi - 1.0) < 0.01
    assert y2025.totals.calories == 250.0


def test_months_last_24_most_recent_first():
    user = _user()
    result = build_months_list(user, count=24)
    assert len(result.months) == 24
    first = result.months[0]
    second = result.months[1]
    assert first.is_current is True
    assert (first.year, first.month) > (second.year, second.month)
