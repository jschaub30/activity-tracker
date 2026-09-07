#!/usr/bin/env python3
"""One-shot import of backend/data/garmin_tracker.db into DynamoDB.

Requires DYNAMODB_TABLE (and optional DYNAMODB_ENDPOINT / AWS_REGION).
Does not copy activity raw_json.
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND / "src"))

from garmin_tracker.config import get_settings  # noqa: E402
from garmin_tracker.db import init_db  # noqa: E402
from garmin_tracker.models import (  # noqa: E402
    Activity,
    ActivityCategory,
    GarminSession,
    ReviewStatus,
    ShareLink,
    SyncRun,
    SyncStatus,
    User,
)
from garmin_tracker.store import repo  # noqa: E402
from garmin_tracker.store.client import ensure_table  # noqa: E402


def _dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main() -> None:
    db_path = BACKEND / "data" / "garmin_tracker.db"
    if not db_path.exists():
        print(f"No SQLite db at {db_path}")
        sys.exit(1)

    settings = get_settings()
    print(f"Importing {db_path} → table {settings.dynamodb_table}")
    if settings.dynamodb_endpoint:
        ensure_table()
    else:
        init_db()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    for row in conn.execute("SELECT * FROM users"):
        try:
            repo.create_user(
                User(
                    id=row["id"],
                    email=row["email"],
                    password_hash=row["password_hash"],
                    timezone=row["timezone"] or "America/Denver",
                    created_at=_dt(row["created_at"]) or datetime.now(timezone.utc),
                )
            )
        except ValueError:
            print(f"skip existing user {row['email']}")

    for row in conn.execute("SELECT * FROM garmin_sessions"):
        repo.put_garmin(
            GarminSession(
                id=row["id"],
                user_id=row["user_id"],
                encrypted_token=row["encrypted_token"],
                garmin_email=row["garmin_email"],
                connected_at=_dt(row["connected_at"]) or datetime.now(timezone.utc),
                last_success_at=_dt(row["last_success_at"]),
                last_error=row["last_error"],
            )
        )

    for row in conn.execute("SELECT * FROM activities"):
        repo.put_activity(
            Activity(
                id=row["id"],
                user_id=row["user_id"],
                garmin_activity_id=row["garmin_activity_id"],
                name=row["name"] or "",
                start_time=_dt(row["start_time"]) or datetime.now(timezone.utc),
                garmin_type=row["garmin_type"] or "",
                suggested_category=ActivityCategory(row["suggested_category"] or "uncategorized"),
                category=ActivityCategory(row["category"] or "uncategorized"),
                review_status=ReviewStatus(row["review_status"] or "pending"),
                distance_m=row["distance_m"],
                elevation_gain_m=row["elevation_gain_m"],
                duration_s=row["duration_s"],
                active_calories=row["active_calories"],
                avg_hr=row["avg_hr"],
                max_hr=row["max_hr"],
                calories=row["calories"],
                synced_at=_dt(row["synced_at"]) or datetime.now(timezone.utc),
                updated_at=_dt(row["updated_at"]) or datetime.now(timezone.utc),
            )
        )

    for row in conn.execute("SELECT * FROM sync_runs"):
        repo.put_sync_run(
            SyncRun(
                id=row["id"],
                user_id=row["user_id"],
                status=SyncStatus(row["status"] or "success"),
                started_at=_dt(row["started_at"]) or datetime.now(timezone.utc),
                finished_at=_dt(row["finished_at"]),
                range_start=_dt(row["range_start"]),
                range_end=_dt(row["range_end"]),
                activities_fetched=row["activities_fetched"] or 0,
                activities_created=row["activities_created"] or 0,
                activities_updated=row["activities_updated"] or 0,
                error=row["error"],
            )
        )

    for row in conn.execute("SELECT * FROM share_links"):
        repo.put_share_link(
            ShareLink(
                id=row["id"],
                user_id=row["user_id"],
                token=row["token"],
                label=row["label"],
                created_at=_dt(row["created_at"]) or datetime.now(timezone.utc),
                revoked_at=_dt(row["revoked_at"]),
            )
        )

    print("Done.")


if __name__ == "__main__":
    main()
