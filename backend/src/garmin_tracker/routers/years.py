from fastapi import APIRouter

from garmin_tracker.deps import CurrentUser
from garmin_tracker.schemas import YearsListOut
from garmin_tracker.services.period_service import build_years_list

router = APIRouter(prefix="/api/years", tags=["years"])


@router.get("", response_model=YearsListOut)
def list_years(user: CurrentUser) -> YearsListOut:
    return build_years_list(user)
