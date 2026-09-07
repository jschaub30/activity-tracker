"""Month and year summaries in the user's timezone (America/Denver by default)."""

from __future__ import annotations

from calendar import monthrange
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from garmin_tracker.models import WEEK_SUMMARY_CATEGORIES, Activity, User
from garmin_tracker.schemas import (
    MonthOut,
    MonthsListOut,
    WeekTotalsOut,
    YearMonthOut,
    YearOut,
    YearsListOut,
)
from garmin_tracker.store import repo
from garmin_tracker.units import m_to_ft, m_to_mi

MONTH_ABBR = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def _tz(user: User) -> ZoneInfo:
    return ZoneInfo(user.timezone or "America/Denver")


def _local_date(act: Activity, tz: ZoneInfo) -> date:
    st = act.start_time
    if st.tzinfo is None:
        st = st.replace(tzinfo=UTC)
    return st.astimezone(tz).date()


def totals_from_activities(activities: list[Activity]) -> WeekTotalsOut:
    summary_cats = set(WEEK_SUMMARY_CATEGORIES)
    total_m = 0.0
    total_elev_m = 0.0
    total_cal = 0.0
    for act in activities:
        cal = float(
            act.calories if act.calories is not None else (act.active_calories or 0.0)
        )
        total_cal += cal
        if act.category in summary_cats:
            total_m += act.distance_m or 0.0
            total_elev_m += act.elevation_gain_m or 0.0
    return WeekTotalsOut(
        distance_mi=m_to_mi(total_m) or 0.0,
        elevation_ft=m_to_ft(total_elev_m) or 0.0,
        calories=round(total_cal, 0),
    )


def _empty_totals() -> WeekTotalsOut:
    return WeekTotalsOut(distance_mi=0.0, elevation_ft=0.0, calories=0.0)


def build_months_list(user: User, count: int = 48) -> MonthsListOut:
    count = max(1, min(count, 120))
    tz = _tz(user)
    today = datetime.now(tz).date()
    year, month = today.year, today.month
    acts = repo.list_activities(user.id)
    by_key: dict[tuple[int, int], list[Activity]] = {}
    for act in acts:
        d = _local_date(act, tz)
        by_key.setdefault((d.year, d.month), []).append(act)

    months: list[MonthOut] = []
    for _ in range(count):
        key = (year, month)
        last_day = monthrange(year, month)[1]
        months.append(
            MonthOut(
                year=year,
                month=month,
                label=f"{MONTH_ABBR[month - 1]} {year}",
                start=date(year, month, 1).isoformat(),
                end=date(year, month, last_day).isoformat(),
                is_current=year == today.year and month == today.month,
                totals=totals_from_activities(by_key.get(key, [])),
            )
        )
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return MonthsListOut(timezone=user.timezone or "America/Denver", months=months)


def build_years_list(user: User) -> YearsListOut:
    tz = _tz(user)
    today = datetime.now(tz).date()
    acts = repo.list_activities(user.id)
    by_year_month: dict[int, dict[int, list[Activity]]] = {}
    for act in acts:
        d = _local_date(act, tz)
        by_year_month.setdefault(d.year, {}).setdefault(d.month, []).append(act)

    if by_year_month:
        oldest = min(by_year_month)
        years = list(range(today.year, oldest - 1, -1))
    else:
        years = [today.year]

    out: list[YearOut] = []
    for year in years:
        is_ytd = year == today.year
        month_outs: list[YearMonthOut] = []
        year_acts: list[Activity] = []
        for m in range(1, 13):
            if is_ytd and m > today.month:
                month_outs.append(YearMonthOut(month=m, totals=_empty_totals()))
                continue
            chunk = by_year_month.get(year, {}).get(m, [])
            year_acts.extend(chunk)
            month_outs.append(
                YearMonthOut(month=m, totals=totals_from_activities(chunk))
            )
        out.append(
            YearOut(
                year=year,
                is_ytd=is_ytd,
                label="YTD" if is_ytd else str(year),
                months=month_outs,
                totals=totals_from_activities(year_acts),
            )
        )
    return YearsListOut(timezone=user.timezone or "America/Denver", years=out)
