from datetime import date, timedelta
from unittest.mock import MagicMock

from garmin_tracker.services.week_service import build_weeks_list, sunday_on_or_before


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
