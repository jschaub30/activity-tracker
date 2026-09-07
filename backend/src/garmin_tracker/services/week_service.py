"""Build Sunday–Saturday week summaries in America/Denver."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from garmin_tracker.models import WEEK_SUMMARY_CATEGORIES, Activity, User
from garmin_tracker.schemas import (
    WeekActivityOut,
    WeekDayOut,
    WeekOut,
    WeeksListOut,
    WeekTotalsOut,
)
from garmin_tracker.store import repo
from garmin_tracker.units import m_to_ft, m_to_mi


def sunday_on_or_before(d: date) -> date:
    # Monday=0 ... Sunday=6 in date.weekday(); we want Sunday start
    days_since_sunday = (d.weekday() + 1) % 7
    return d - timedelta(days=days_since_sunday)


def parse_week_start(week_start: str | None, tz_name: str) -> date:
    tz = ZoneInfo(tz_name)
    if week_start:
        d = date.fromisoformat(week_start)
        return sunday_on_or_before(d)
    today = datetime.now(tz).date()
    return sunday_on_or_before(today)


def week_bounds_utc(week_start: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    week_end = week_start + timedelta(days=6)
    start_dt = datetime.combine(week_start, datetime.min.time(), tzinfo=tz)
    end_dt = datetime.combine(week_end, datetime.max.time(), tzinfo=tz)
    return start_dt.astimezone(UTC), end_dt.astimezone(UTC)


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _fetch_week_activities(
    user: User,
    week_start: date,
    tz: ZoneInfo,
) -> list[Activity]:
    """All activities for the week (any category)."""
    start_utc, end_utc = week_bounds_utc(week_start, tz)
    return repo.list_activities(
        user.id, start_iso=_iso_z(start_utc), end_iso=_iso_z(end_utc)
    )


def week_from_activities(
    user: User,
    week_start: date,
    activities: list[Activity],
) -> WeekOut:
    tz_name = user.timezone or "America/Denver"
    tz = ZoneInfo(tz_name)
    week_end = week_start + timedelta(days=6)
    by_day: dict[str, list[WeekActivityOut]] = {
        (week_start + timedelta(days=i)).isoformat(): [] for i in range(7)
    }
    total_m = 0.0
    total_elev_m = 0.0
    total_cal = 0.0
    summary_cats = set(WEEK_SUMMARY_CATEGORIES)

    for act in activities:
        st = act.start_time
        if st.tzinfo is None:
            st = st.replace(tzinfo=UTC)
        local_date = st.astimezone(tz).date().isoformat()
        dist_mi = m_to_mi(act.distance_m) or 0.0
        elev_ft = m_to_ft(act.elevation_gain_m) or 0.0
        cal = float(
            act.calories if act.calories is not None else (act.active_calories or 0.0)
        )
        if local_date in by_day:
            by_day[local_date].append(
                WeekActivityOut(
                    id=act.id,
                    name=act.name,
                    category=act.category,
                    distance_mi=dist_mi,
                    elevation_ft=elev_ft,
                    calories=round(cal, 0),
                    duration_s=act.duration_s,
                )
            )
            if act.category in summary_cats:
                total_m += act.distance_m or 0.0
                total_elev_m += act.elevation_gain_m or 0.0
            total_cal += cal

    days = [WeekDayOut(date=d, activities=by_day[d]) for d in sorted(by_day.keys())]
    return WeekOut(
        week_start=week_start.isoformat(),
        week_end=week_end.isoformat(),
        timezone=tz_name,
        days=days,
        totals=WeekTotalsOut(
            distance_mi=m_to_mi(total_m) or 0.0,
            elevation_ft=m_to_ft(total_elev_m) or 0.0,
            calories=round(total_cal, 0),
        ),
    )


def persist_week(user: User, week: WeekOut) -> None:
    repo.put_week(user.id, week.week_start, week.model_dump(mode="json"))


def build_week(user: User, week_start_str: str | None = None) -> WeekOut:
    tz_name = user.timezone or "America/Denver"
    tz = ZoneInfo(tz_name)
    week_start = parse_week_start(week_start_str, tz_name)
    activities = _fetch_week_activities(user, week_start, tz)
    week = week_from_activities(user, week_start, activities)
    persist_week(user, week)
    return week


def rebuild_weeks_for_times(user: User, times: list[datetime]) -> None:
    tz_name = user.timezone or "America/Denver"
    tz = ZoneInfo(tz_name)
    sundays: set[date] = set()
    for st in times:
        if st.tzinfo is None:
            st = st.replace(tzinfo=UTC)
        sundays.add(sunday_on_or_before(st.astimezone(tz).date()))
    for sunday in sundays:
        build_week(user, sunday.isoformat())


def build_weeks_list(user: User, count: int = 52) -> WeeksListOut:
    """Return `count` full weeks (Sun–Sat + totals), most recent first."""
    count = max(1, min(count, 104))
    tz_name = user.timezone or "America/Denver"
    tz = ZoneInfo(tz_name)
    current_sunday = parse_week_start(None, tz_name)
    oldest = current_sunday - timedelta(weeks=count - 1)
    start_utc, _ = week_bounds_utc(oldest, tz)
    _, end_utc = week_bounds_utc(current_sunday, tz)
    acts = repo.list_activities(
        user.id, start_iso=_iso_z(start_utc), end_iso=_iso_z(end_utc)
    )
    by_sunday: dict[str, list[Activity]] = {}
    for act in acts:
        st = act.start_time
        if st.tzinfo is None:
            st = st.replace(tzinfo=UTC)
        sunday = sunday_on_or_before(st.astimezone(tz).date()).isoformat()
        by_sunday.setdefault(sunday, []).append(act)

    weeks: list[WeekOut] = []
    for i in range(count):
        week_start = current_sunday - timedelta(weeks=i)
        key = week_start.isoformat()
        week = week_from_activities(user, week_start, by_sunday.get(key, []))
        persist_week(user, week)
        weeks.append(week)
    return WeeksListOut(timezone=tz_name, weeks=weeks)
