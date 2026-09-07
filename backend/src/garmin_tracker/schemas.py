from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from garmin_tracker.models import (
    ActivityCategory,
    DisplayUnits,
    ReviewStatus,
    SyncStatus,
)

# ----- Auth -----


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: EmailStr
    timezone: str
    units: DisplayUnits = DisplayUnits.imperial

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    units: DisplayUnits | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ----- Garmin -----


class GarminConnectRequest(BaseModel):
    email: EmailStr
    password: str


class GarminMfaRequest(BaseModel):
    code: str = Field(min_length=4, max_length=12)


class GarminStatusOut(BaseModel):
    connected: bool
    garmin_email: str | None = None
    connected_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error: str | None = None


class GarminConnectResult(GarminStatusOut):
    needs_mfa: bool = False
    message: str | None = None


# ----- Activities -----


class ActivityOut(BaseModel):
    id: str
    garmin_activity_id: str
    name: str
    start_time: datetime
    garmin_type: str
    suggested_category: ActivityCategory
    category: ActivityCategory
    review_status: ReviewStatus
    distance_m: float | None = None
    elevation_gain_m: float | None = None
    distance_mi: float | None = None
    elevation_ft: float | None = None
    duration_s: float | None = None
    active_calories: float | None = None
    avg_hr: float | None = None
    max_hr: float | None = None
    calories: float | None = None

    model_config = {"from_attributes": True}


class ActivityUpdate(BaseModel):
    category: ActivityCategory | None = None


# ----- Weeks -----


class WeekActivityOut(BaseModel):
    id: str
    name: str
    garmin_type: str = ""
    category: ActivityCategory
    distance_mi: float
    elevation_ft: float
    calories: float = 0.0
    duration_s: float | None = None


class WeekDayOut(BaseModel):
    date: str  # YYYY-MM-DD in America/Denver
    activities: list[WeekActivityOut]


class WeekTotalsOut(BaseModel):
    distance_mi: float
    elevation_ft: float
    calories: float = 0.0


class WeekOut(BaseModel):
    week_start: str
    week_end: str
    timezone: str
    days: list[WeekDayOut]
    totals: WeekTotalsOut


class WeeksListOut(BaseModel):
    """Stacked week grid: each week has Sun–Sat days + totals (most recent first)."""

    timezone: str
    weeks: list[WeekOut]  # most recent first


class MonthOut(BaseModel):
    year: int
    month: int
    label: str
    start: str
    end: str
    is_current: bool = False
    totals: WeekTotalsOut


class MonthsListOut(BaseModel):
    timezone: str
    months: list[MonthOut]  # most recent first


class YearMonthOut(BaseModel):
    month: int
    totals: WeekTotalsOut


class YearOut(BaseModel):
    year: int
    is_ytd: bool
    label: str
    months: list[YearMonthOut]
    totals: WeekTotalsOut


class YearsListOut(BaseModel):
    timezone: str
    years: list[YearOut]  # YTD first, then prior years


# ----- Sync -----


class SyncStatusOut(BaseModel):
    id: str | None = None
    status: SyncStatus | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    activities_fetched: int = 0
    activities_created: int = 0
    activities_updated: int = 0
    error: str | None = None
    is_running: bool = False


class SyncStartOut(BaseModel):
    message: str
    sync_run_id: str


# ----- Share links -----


class ShareLinkCreate(BaseModel):
    label: str | None = Field(default=None, max_length=120)


class ShareLinkOut(BaseModel):
    id: str
    token: str
    label: str | None = None
    created_at: datetime
    revoked_at: datetime | None = None
    # Absolute path on the SPA (frontend prefixes origin)
    path: str

    model_config = {"from_attributes": True}


class PublicShareMeta(BaseModel):
    """Minimal public metadata for a valid share token."""

    label: str | None = None
    timezone: str
    # Non-identifying display name (email local-part only)
    owner_display: str
    units: DisplayUnits = DisplayUnits.imperial


# ----- Account -----


class DeleteDataOut(BaseModel):
    activities_deleted: int
    sync_runs_deleted: int
    message: str
