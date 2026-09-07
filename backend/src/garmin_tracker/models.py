"""Domain types. Persistence is DynamoDB (see garmin_tracker.store)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid4())


class ActivityCategory(StrEnum):
    run = "run"
    hike = "hike"
    stair = "stair"  # stair stepper / stair climbing — included in week summary
    cardio = "cardio"
    strength = "strength"
    uncategorized = "uncategorized"


# Categories that contribute to week distance/elevation totals.
# All confirmed activities appear on the grid; calories sum every category.
WEEK_SUMMARY_CATEGORIES = (
    ActivityCategory.run,
    ActivityCategory.hike,
    ActivityCategory.stair,
)


class ReviewStatus(StrEnum):
    pending = "pending"
    confirmed = "confirmed"


class SyncStatus(StrEnum):
    running = "running"
    success = "success"
    failed = "failed"


@dataclass
class User:
    id: str
    email: str
    password_hash: str
    timezone: str = "America/Denver"
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class GarminSession:
    """Per-user encrypted Garmin Connect session (garth tokens)."""

    user_id: str
    encrypted_token: str
    id: str = field(default_factory=new_id)
    garmin_email: str | None = None
    connected_at: datetime = field(default_factory=utcnow)
    last_success_at: datetime | None = None
    last_error: str | None = None


@dataclass
class Activity:
    user_id: str
    garmin_activity_id: str
    id: str = field(default_factory=new_id)
    name: str = ""
    start_time: datetime = field(default_factory=utcnow)
    garmin_type: str = ""
    suggested_category: ActivityCategory = ActivityCategory.uncategorized
    category: ActivityCategory = ActivityCategory.uncategorized
    review_status: ReviewStatus = ReviewStatus.confirmed
    distance_m: float | None = None
    elevation_gain_m: float | None = None
    duration_s: float | None = None
    active_calories: float | None = None
    avg_hr: float | None = None
    max_hr: float | None = None
    calories: float | None = None
    raw_json: str | None = None
    synced_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class SyncRun:
    user_id: str
    id: str = field(default_factory=new_id)
    status: SyncStatus = SyncStatus.running
    started_at: datetime = field(default_factory=utcnow)
    finished_at: datetime | None = None
    range_start: datetime | None = None
    range_end: datetime | None = None
    activities_fetched: int = 0
    activities_created: int = 0
    activities_updated: int = 0
    error: str | None = None
    # Worker cursor (YYYY-MM-DD) for chunked backfill; None = start of range
    cursor: str | None = None
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class ShareLink:
    """Public read-only share token for weeks + charts."""

    user_id: str
    token: str
    id: str = field(default_factory=new_id)
    label: str | None = None
    created_at: datetime = field(default_factory=utcnow)
    revoked_at: datetime | None = None
