from fastapi import APIRouter, Query

from garmin_tracker.deps import CurrentUser
from garmin_tracker.schemas import MonthsListOut
from garmin_tracker.services.period_service import build_months_list

router = APIRouter(prefix="/api/months", tags=["months"])


@router.get("", response_model=MonthsListOut)
def list_months(
    user: CurrentUser,
    count: int = Query(default=48, ge=1, le=120),
) -> MonthsListOut:
    return build_months_list(user, count=count)
