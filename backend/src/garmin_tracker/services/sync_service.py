"""Sync activities from Garmin Connect into the local database."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from sqlmodel import Session, select

from garmin_tracker.config import get_settings
from garmin_tracker.models import (
    Activity,
    GarminSession,
    ReviewStatus,
    SyncRun,
    SyncStatus,
    User,
    utcnow,
)
from garmin_tracker.services.activity_normalize import normalize_activity
from garmin_tracker.services.crypto import decrypt_token, encrypt_token
from garmin_tracker.services.garmin_client import GarminClient, GarminClientError

logger = logging.getLogger(__name__)

# Overlap window so late-arriving activities are not missed
INCREMENTAL_OVERLAP_DAYS = 3


class SyncService:
    def __init__(self, session: Session, user: User):
        self.session = session
        self.user = user
        self.settings = get_settings()

    def is_running(self) -> bool:
        stmt = (
            select(SyncRun)
            .where(SyncRun.user_id == self.user.id, SyncRun.status == SyncStatus.running)
            .limit(1)
        )
        return self.session.exec(stmt).first() is not None

    def latest_run(self) -> SyncRun | None:
        stmt = (
            select(SyncRun)
            .where(SyncRun.user_id == self.user.id)
            .order_by(SyncRun.started_at.desc())  # type: ignore[attr-defined]
            .limit(1)
        )
        return self.session.exec(stmt).first()

    def garmin_row(self) -> GarminSession | None:
        return self.session.exec(
            select(GarminSession).where(GarminSession.user_id == self.user.id)
        ).first()

    def create_running_sync(self) -> SyncRun:
        if self.is_running():
            raise RuntimeError("A sync is already running for this user")

        garmin = self.garmin_row()
        if not garmin:
            raise RuntimeError("Garmin account not connected")

        range_start, range_end = self._compute_range(garmin)
        run = SyncRun(
            user_id=self.user.id,
            status=SyncStatus.running,
            range_start=datetime.combine(range_start, datetime.min.time(), tzinfo=timezone.utc),
            range_end=datetime.combine(range_end, datetime.max.time(), tzinfo=timezone.utc),
        )
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def _compute_range(self, garmin: GarminSession) -> tuple[date, date]:
        today = datetime.now(timezone.utc).date()
        if garmin.last_success_at:
            last = garmin.last_success_at
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            start = (last - timedelta(days=INCREMENTAL_OVERLAP_DAYS)).date()
        else:
            start = today - timedelta(days=self.settings.backfill_days)
        return start, today

    def execute_sync(self, run_id: str) -> SyncRun:
        """Fetch from Garmin and upsert. Call from request or background worker."""
        run = self.session.get(SyncRun, run_id)
        if not run or run.user_id != self.user.id:
            raise RuntimeError("Sync run not found")

        garmin = self.garmin_row()
        if not garmin:
            return self._fail(run, "Garmin account not connected")

        try:
            token = decrypt_token(garmin.encrypted_token)
        except Exception as exc:  # noqa: BLE001
            return self._fail(run, f"Could not decrypt Garmin session: {exc}")

        try:
            client = GarminClient(email=garmin.garmin_email)
            client.load_session(token)
            range_start, range_end = self._compute_range(garmin)
            activities = client.get_activities(range_start, range_end)

            # Persist refreshed tokens
            try:
                garmin.encrypted_token = encrypt_token(client.dump_session())
            except Exception:  # noqa: BLE001
                logger.debug("Could not re-encrypt refreshed tokens", exc_info=True)

            created, updated = self._upsert_activities(activities)

            run.activities_fetched = len(activities)
            run.activities_created = created
            run.activities_updated = updated
            run.status = SyncStatus.success
            run.finished_at = utcnow()
            run.error = None
            run.range_start = datetime.combine(
                range_start, datetime.min.time(), tzinfo=timezone.utc
            )
            run.range_end = datetime.combine(
                range_end, datetime.max.time(), tzinfo=timezone.utc
            )

            garmin.last_success_at = utcnow()
            garmin.last_error = None
            self.session.add(garmin)
            self.session.add(run)
            self.session.commit()
            self.session.refresh(run)
            return run

        except GarminClientError as exc:
            return self._fail(run, str(exc), garmin=garmin)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Sync failed for user %s", self.user.id)
            return self._fail(run, f"Sync failed: {exc}", garmin=garmin)

    def start_sync(self) -> SyncRun:
        """Create run and execute inline (simple local path)."""
        run = self.create_running_sync()
        return self.execute_sync(run.id)

    def _upsert_activities(self, activities: list[dict]) -> tuple[int, int]:
        created = 0
        updated = 0
        now = utcnow()

        for raw in activities:
            try:
                data = normalize_activity(raw)
            except ValueError:
                logger.debug("Skipping unparseable activity: %s", raw.get("activityId"))
                continue

            existing = self.session.exec(
                select(Activity).where(
                    Activity.user_id == self.user.id,
                    Activity.garmin_activity_id == data["garmin_activity_id"],
                )
            ).first()

            if existing:
                existing.name = data["name"]
                existing.start_time = data["start_time"]
                existing.garmin_type = data["garmin_type"]
                existing.suggested_category = data["suggested_category"]
                # Do not override user-confirmed category / review
                if existing.review_status != ReviewStatus.confirmed:
                    existing.category = data["suggested_category"]
                existing.distance_m = data["distance_m"]
                existing.elevation_gain_m = data["elevation_gain_m"]
                existing.duration_s = data["duration_s"]
                existing.active_calories = data["active_calories"]
                existing.calories = data["calories"]
                existing.avg_hr = data["avg_hr"]
                existing.max_hr = data["max_hr"]
                existing.raw_json = data["raw_json"]
                existing.synced_at = now
                existing.updated_at = now
                self.session.add(existing)
                updated += 1
            else:
                act = Activity(
                    user_id=self.user.id,
                    garmin_activity_id=data["garmin_activity_id"],
                    name=data["name"],
                    start_time=data["start_time"],
                    garmin_type=data["garmin_type"],
                    suggested_category=data["suggested_category"],
                    category=data["suggested_category"],
                    review_status=ReviewStatus.pending,
                    distance_m=data["distance_m"],
                    elevation_gain_m=data["elevation_gain_m"],
                    duration_s=data["duration_s"],
                    active_calories=data["active_calories"],
                    calories=data["calories"],
                    avg_hr=data["avg_hr"],
                    max_hr=data["max_hr"],
                    raw_json=data["raw_json"],
                    synced_at=now,
                    updated_at=now,
                )
                self.session.add(act)
                created += 1

        self.session.commit()
        return created, updated

    def _fail(
        self,
        run: SyncRun,
        message: str,
        garmin: GarminSession | None = None,
    ) -> SyncRun:
        run.status = SyncStatus.failed
        run.finished_at = utcnow()
        run.error = message
        self.session.add(run)
        if garmin:
            garmin.last_error = message
            self.session.add(garmin)
        self.session.commit()
        self.session.refresh(run)
        return run
