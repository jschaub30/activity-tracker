from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from garmin_tracker.models import ActivityCategory, ReviewStatus, SyncStatus


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

    model_config = {"from_attributes": True}


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
    garmin_email: Optional[str] = None
    connected_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_error: Optional[str] = None


class GarminConnectResult(GarminStatusOut):
    needs_mfa: bool = False
    message: Optional[str] = None


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
    distance_m: Optional[float] = None
    elevation_gain_m: Optional[float] = None
    distance_mi: Optional[float] = None
    elevation_ft: Optional[float] = None
    duration_s: Optional[float] = None
    active_calories: Optional[float] = None
    avg_hr: Optional[float] = None
    max_hr: Optional[float] = None
    calories: Optional[float] = None

    model_config = {"from_attributes": True}


class ActivityUpdate(BaseModel):
    category: Optional[ActivityCategory] = None
    review_status: Optional[ReviewStatus] = None


class BulkConfirmRequest(BaseModel):
    activity_ids: Optional[list[str]] = None  # None = confirm all pending for user
    accept_suggested: bool = True


# ----- Weeks -----


class WeekActivityOut(BaseModel):
    id: str
    name: str
    category: ActivityCategory
    distance_mi: float
    elevation_ft: float
    calories: float = 0.0
    duration_s: Optional[float] = None


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


# ----- Sync -----


class SyncStatusOut(BaseModel):
    id: Optional[str] = None
    status: Optional[SyncStatus] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    activities_fetched: int = 0
    activities_created: int = 0
    activities_updated: int = 0
    error: Optional[str] = None
    is_running: bool = False


class SyncStartOut(BaseModel):
    message: str
    sync_run_id: str


# ----- Share links -----


class ShareLinkCreate(BaseModel):
    label: Optional[str] = Field(default=None, max_length=120)


class ShareLinkOut(BaseModel):
    id: str
    token: str
    label: Optional[str] = None
    created_at: datetime
    revoked_at: Optional[datetime] = None
    # Absolute path on the SPA (frontend prefixes origin)
    path: str

    model_config = {"from_attributes": True}


class PublicShareMeta(BaseModel):
    """Minimal public metadata for a valid share token."""

    label: Optional[str] = None
    timezone: str
    # Non-identifying display name (email local-part only)
    owner_display: str
