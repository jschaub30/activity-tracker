"""Build Sunday–Saturday week summaries in America/Denver."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlmodel import Session, select

from garmin_tracker.models import WEEK_SUMMARY_CATEGORIES, Activity, ReviewStatus, User
from garmin_tracker.schemas import (
    WeekActivityOut,
    WeekDayOut,
    WeekOut,
    WeeksListOut,
    WeekTotalsOut,
)
from garmin_tracker.units import m_to_ft, m_to_mi


def sunday_on_or_before(d: date) -> date:
    # Monday=0 ... Sunday=6 in date.weekday(); we want Sunday start
    # date.weekday(): Mon=0 .. Sun=6
    days_since_sunday = (d.weekday() + 1) % 7
    return d - timedelta(days=days_since_sunday)


def parse_week_start(week_start: str | None, tz_name: str) -> date:
    tz = ZoneInfo(tz_name)
    if week_start:
        d = date.fromisoformat(week_start)
        return sunday_on_or_before(d)
    today = datetime.now(tz).date()
    return sunday_on_or_before(today)


def _fetch_confirmed_week_activities(
    session: Session,
    user: User,
    week_start: date,
    tz: ZoneInfo,
) -> list[Activity]:
    week_end = week_start + timedelta(days=6)
    start_dt = datetime.combine(week_start, datetime.min.time(), tzinfo=tz)
    end_dt = datetime.combine(week_end, datetime.max.time(), tzinfo=tz)
    start_utc = start_dt.astimezone(timezone.utc)
    end_utc = end_dt.astimezone(timezone.utc)

    stmt = (
        select(Activity)
        .where(
            Activity.user_id == user.id,
            Activity.review_status == ReviewStatus.confirmed,
            Activity.category.in_(list(WEEK_SUMMARY_CATEGORIES)),  # type: ignore[attr-defined]
            Activity.start_time >= start_utc,
            Activity.start_time <= end_utc,
        )
        .order_by(Activity.start_time.asc())  # type: ignore[attr-defined]
    )
    return list(session.exec(stmt).all())


def build_week(session: Session, user: User, week_start_str: str | None = None) -> WeekOut:
    tz_name = user.timezone or "America/Denver"
    tz = ZoneInfo(tz_name)
    week_start = parse_week_start(week_start_str, tz_name)
    week_end = week_start + timedelta(days=6)

    activities = _fetch_confirmed_week_activities(session, user, week_start, tz)

    by_day: dict[str, list[WeekActivityOut]] = {
        (week_start + timedelta(days=i)).isoformat(): [] for i in range(7)
    }

    total_m = 0.0
    total_elev_m = 0.0
    total_cal = 0.0

    for act in activities:
        st = act.start_time
        if st.tzinfo is None:
            st = st.replace(tzinfo=timezone.utc)
        local_date = st.astimezone(tz).date().isoformat()
        dist_mi = m_to_mi(act.distance_m) or 0.0
        elev_ft = m_to_ft(act.elevation_gain_m) or 0.0
        # Garmin primary field is "calories"
        cal = float(act.calories if act.calories is not None else (act.active_calories or 0.0))
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
            total_m += act.distance_m or 0.0
            total_elev_m += act.elevation_gain_m or 0.0
            total_cal += cal

    days = [
        WeekDayOut(date=d, activities=by_day[d])
        for d in sorted(by_day.keys())
    ]

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


def build_weeks_list(
    session: Session,
    user: User,
    count: int = 52,
) -> WeeksListOut:
    """Return `count` full weeks (Sun–Sat + totals), most recent first."""
    count = max(1, min(count, 104))
    tz_name = user.timezone or "America/Denver"
    current_sunday = parse_week_start(None, tz_name)

    weeks: list[WeekOut] = []
    for i in range(count):
        week_start = current_sunday - timedelta(weeks=i)
        weeks.append(build_week(session, user, week_start.isoformat()))

    return WeeksListOut(timezone=tz_name, weeks=weeks)
