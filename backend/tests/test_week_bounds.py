from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock

from garmin_tracker.models import ActivityCategory
from garmin_tracker.services.week_service import (
    build_week,
    build_weeks_list,
    sunday_on_or_before,
)


def test_sunday_on_or_before():
    # 2026-07-11 is Saturday → week starts 2026-07-05 (Sunday)
    assert sunday_on_or_before(date(2026, 7, 11)) == date(2026, 7, 5)
    # Sunday stays Sunday
    assert sunday_on_or_before(date(2026, 7, 5)) == date(2026, 7, 5)
    # Monday → previous Sunday
    assert sunday_on_or_before(date(2026, 7, 6)) == date(2026, 7, 5)


def test_weeks_list_order_and_count(monkeypatch):
    user = MagicMock()
    user.id = "u1"
    user.timezone = "America/Denver"
    session = MagicMock()

    monkeypatch.setattr(
        "garmin_tracker.services.week_service._fetch_confirmed_week_activities",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        "garmin_tracker.services.week_service.parse_week_start",
        lambda week_start, tz_name: (
            date.fromisoformat(week_start)
            if week_start
            else date(2026, 7, 5)
        ),
    )

    result = build_weeks_list(session, user, count=52)
    assert len(result.weeks) == 52
    # Full day detail, most recent first
    assert result.weeks[0].week_start == "2026-07-05"
    assert len(result.weeks[0].days) == 7
    assert result.weeks[0].days[0].date.endswith("-05") or result.weeks[0].days[0].date == "2026-07-05"
    assert result.weeks[1].week_start == "2026-06-28"
    assert result.weeks[-1].week_start == (
        date(2026, 7, 5) - timedelta(weeks=51)
    ).isoformat()


def _act(
    *,
    id: str,
    category: ActivityCategory,
    start: datetime,
    distance_m: float = 0.0,
    elevation_gain_m: float = 0.0,
    calories: float = 0.0,
) -> MagicMock:
    a = MagicMock()
    a.id = id
    a.name = id
    a.category = category
    a.start_time = start
    a.distance_m = distance_m
    a.elevation_gain_m = elevation_gain_m
    a.calories = calories
    a.active_calories = None
    a.duration_s = 1800.0
    return a


def test_week_calories_include_all_categories(monkeypatch):
    """Distance/elev only for run/hike/stair; calories sum all confirmed."""
    user = MagicMock()
    user.id = "u1"
    user.timezone = "America/Denver"
    session = MagicMock()

    # Monday 2026-07-06 12:00 Denver = 18:00 UTC (MDT)
    mon = datetime(2026, 7, 6, 18, 0, tzinfo=timezone.utc)
    activities = [
        _act(
            id="run1",
            category=ActivityCategory.run,
            start=mon,
            distance_m=1609.34,  # 1 mi
            elevation_gain_m=30.48,  # 100 ft
            calories=400,
        ),
        _act(
            id="strength1",
            category=ActivityCategory.strength,
            start=mon.replace(hour=20),
            distance_m=5000,  # should not affect distance total
            elevation_gain_m=100,  # should not affect elev total
            calories=250,
        ),
        _act(
            id="cardio1",
            category=ActivityCategory.cardio,
            start=mon.replace(hour=22),
            calories=150,
        ),
    ]

    monkeypatch.setattr(
        "garmin_tracker.services.week_service._fetch_confirmed_week_activities",
        lambda *args, **kwargs: activities,
    )

    week = build_week(session, user, "2026-07-05")
    assert week.totals.calories == 800.0
    assert abs(week.totals.distance_mi - 1.0) < 0.01
    assert abs(week.totals.elevation_ft - 100.0) < 0.5
    # Strength + cardio still appear on the day grid
    mon_acts = next(d.activities for d in week.days if d.date == "2026-07-06")
    assert {a.category for a in mon_acts} == {
        ActivityCategory.run,
        ActivityCategory.strength,
        ActivityCategory.cardio,
    }
