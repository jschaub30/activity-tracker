from fastapi import APIRouter, Query

from garmin_tracker.deps import CurrentUser, SessionDep
from garmin_tracker.schemas import WeekOut, WeeksListOut
from garmin_tracker.services.week_service import build_week, build_weeks_list

router = APIRouter(prefix="/api/weeks", tags=["weeks"])


@router.get("", response_model=WeeksListOut)
def list_weeks(
    session: SessionDep,
    user: CurrentUser,
    count: int = Query(default=52, ge=1, le=104, description="Number of weeks (most recent first)"),
) -> WeeksListOut:
    """Main page: one row per week for the last N weeks."""
    return build_weeks_list(session, user, count=count)


@router.get("/detail", response_model=WeekOut)
def get_week_detail(
    session: SessionDep,
    user: CurrentUser,
    start: str | None = Query(
        default=None,
        description="Any date in the target week (YYYY-MM-DD). Week is Sun–Sat in user timezone.",
    ),
) -> WeekOut:
    """Single week with Sun–Sat day breakdown."""
    return build_week(session, user, start)
