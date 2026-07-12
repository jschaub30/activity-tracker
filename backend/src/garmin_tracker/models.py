from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class ActivityCategory(str, Enum):
    run = "run"
    hike = "hike"
    stair = "stair"  # stair stepper / stair climbing — included in week summary
    cardio = "cardio"
    strength = "strength"
    uncategorized = "uncategorized"


# Categories that appear on the Sunday–Saturday week grid (combined mi/ft totals)
WEEK_SUMMARY_CATEGORIES = (
    ActivityCategory.run,
    ActivityCategory.hike,
    ActivityCategory.stair,
)


class ReviewStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"


class SyncStatus(str, Enum):
    running = "running"
    success = "success"
    failed = "failed"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(default_factory=new_id, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    timezone: str = Field(default="America/Denver")
    created_at: datetime = Field(default_factory=utcnow)


class GarminSession(SQLModel, table=True):
    """Per-user encrypted Garmin Connect session (garth tokens)."""

    __tablename__ = "garmin_sessions"

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True, unique=True)
    encrypted_token: str = Field(sa_column=Column(Text))
    garmin_email: Optional[str] = None
    connected_at: datetime = Field(default_factory=utcnow)
    last_success_at: Optional[datetime] = None
    last_error: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))


class Activity(SQLModel, table=True):
    __tablename__ = "activities"
    __table_args__ = (UniqueConstraint("user_id", "garmin_activity_id", name="uq_user_garmin_activity"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    garmin_activity_id: str = Field(index=True)

    name: str = ""
    start_time: datetime = Field(index=True)
    garmin_type: str = ""

    suggested_category: ActivityCategory = Field(default=ActivityCategory.uncategorized)
    category: ActivityCategory = Field(default=ActivityCategory.uncategorized, index=True)
    review_status: ReviewStatus = Field(default=ReviewStatus.pending, index=True)

    # Stored in metric; convert to mi/ft for display
    distance_m: Optional[float] = None
    elevation_gain_m: Optional[float] = None
    duration_s: Optional[float] = None
    active_calories: Optional[float] = None
    avg_hr: Optional[float] = None
    max_hr: Optional[float] = None
    calories: Optional[float] = None

    raw_json: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

    synced_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class SyncRun(SQLModel, table=True):
    __tablename__ = "sync_runs"

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    status: SyncStatus = Field(default=SyncStatus.running)
    started_at: datetime = Field(default_factory=utcnow)
    finished_at: Optional[datetime] = None
    range_start: Optional[datetime] = None
    range_end: Optional[datetime] = None
    activities_fetched: int = 0
    activities_created: int = 0
    activities_updated: int = 0
    error: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))


class ShareLink(SQLModel, table=True):
    """Public read-only share token for weeks + charts."""

    __tablename__ = "share_links"

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    token: str = Field(index=True, unique=True)
    label: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    revoked_at: Optional[datetime] = None
