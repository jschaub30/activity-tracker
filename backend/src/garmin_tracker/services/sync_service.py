"""Sync activities from Garmin Connect into DynamoDB."""

from __future__ import annotations

import json
import logging
from datetime import UTC, date, datetime, timedelta

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
from garmin_tracker.services.week_service import rebuild_weeks_for_times
from garmin_tracker.store import repo

logger = logging.getLogger(__name__)

INCREMENTAL_OVERLAP_DAYS = 3
# Under the SQS visibility timeout (900s). A run with no cursor bump in this
# window is assumed abandoned (dropped queue message / hung worker).
STALE_SYNC_SECONDS = 8 * 60


class SyncService:
    def __init__(self, user: User):
        self.user = user
        self.settings = get_settings()

    def is_running(self) -> bool:
        return repo.is_sync_running(
            self.user.id, stale_after_seconds=STALE_SYNC_SECONDS
        )

    def _age_seconds(self, run: SyncRun) -> float:
        ts = run.updated_at or run.started_at
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        return (utcnow() - ts).total_seconds()

    def latest_run(self) -> SyncRun | None:
        return repo.latest_sync_run(self.user.id)

    def garmin_row(self) -> GarminSession | None:
        return repo.get_garmin(self.user.id)

    def begin_sync(self) -> SyncRun:
        """Create a new run, or resume a stale in-progress backfill."""
        running = repo.list_running_syncs(self.user.id)
        for run in running:
            if self._age_seconds(run) <= STALE_SYNC_SECONDS:
                raise RuntimeError("A sync is already running for this user")
            logger.warning(
                "Resuming stale sync %s for user %s at cursor %s",
                run.id,
                self.user.id,
                run.cursor,
            )
            run.error = None
            run.updated_at = utcnow()
            repo.put_sync_run(run)
            return run
        return self.create_running_sync()

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
            range_start=datetime.combine(range_start, datetime.min.time(), tzinfo=UTC),
            range_end=datetime.combine(range_end, datetime.max.time(), tzinfo=UTC),
            cursor=range_start.isoformat(),
        )
        repo.put_sync_run(run)
        return run

    def _has_activities(self) -> bool:
        return repo.has_activities(self.user.id)

    def _compute_range(self, garmin: GarminSession) -> tuple[date, date]:
        today = datetime.now(UTC).date()
        if garmin.last_success_at and self._has_activities():
            last = garmin.last_success_at
            if last.tzinfo is None:
                last = last.replace(tzinfo=UTC)
            start = (last - timedelta(days=INCREMENTAL_OVERLAP_DAYS)).date()
        else:
            start = today - timedelta(days=self.settings.backfill_days)
        return start, today

    def execute_sync(self, run_id: str) -> SyncRun:
        """Run remaining chunks inline until the range is done."""
        run = repo.get_sync_run(self.user.id, run_id)
        if not run:
            raise RuntimeError("Sync run not found")
        while True:
            run = self.execute_chunk(run.id)
            if run.status != SyncStatus.running:
                return run

    def execute_chunk(self, run_id: str) -> SyncRun:
        run = repo.get_sync_run(self.user.id, run_id)
        if not run or run.user_id != self.user.id:
            raise RuntimeError("Sync run not found")

        garmin = self.garmin_row()
        if not garmin:
            return self._fail(run, "Garmin account not connected")

        try:
            token = decrypt_token(garmin.encrypted_token)
        except Exception as exc:  # noqa: BLE001
            return self._fail(run, f"Could not decrypt Garmin session: {exc}")

        if not run.range_start or not run.range_end:
            return self._fail(run, "Sync run missing date range")

        chunk_days = max(1, self.settings.sync_chunk_days)
        cursor = (
            date.fromisoformat(run.cursor) if run.cursor else run.range_start.date()
        )
        range_end = run.range_end.date()
        chunk_end = min(cursor + timedelta(days=chunk_days - 1), range_end)
        logger.info(
            "Sync %s user %s chunk %s .. %s (end %s)",
            run.id,
            self.user.id,
            cursor,
            chunk_end,
            range_end,
        )

        try:
            client = GarminClient(email=garmin.garmin_email)
            client.load_session(token)
            activities = client.get_activities(cursor, chunk_end)

            try:
                garmin.encrypted_token = encrypt_token(client.dump_session())
                repo.put_garmin(garmin)
            except Exception:  # noqa: BLE001
                logger.debug("Could not re-encrypt refreshed tokens", exc_info=True)

            created, updated, touched = self._upsert_activities(activities)
            run.activities_fetched += len(activities)
            run.activities_created += created
            run.activities_updated += updated
            rebuild_weeks_for_times(self.user, touched)

            run.updated_at = utcnow()
            more = chunk_end < range_end
            if more:
                run.cursor = (chunk_end + timedelta(days=1)).isoformat()
                run.status = SyncStatus.running
            else:
                run.cursor = None
                run.status = SyncStatus.success
                run.finished_at = utcnow()
                run.error = None
                garmin.last_success_at = utcnow()
                garmin.last_error = None
                repo.put_garmin(garmin)

            repo.put_sync_run(run)
            return run

        except GarminClientError as exc:
            return self._fail(run, str(exc), garmin=garmin)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Sync failed for user %s", self.user.id)
            return self._fail(run, f"Sync failed: {exc}", garmin=garmin)

    def start_sync(self) -> SyncRun:
        run = self.create_running_sync()
        return self.execute_sync(run.id)

    def _upsert_activities(
        self, activities: list[dict]
    ) -> tuple[int, int, list[datetime]]:
        created = 0
        updated = 0
        now = utcnow()
        touched: list[datetime] = []

        for raw in activities:
            try:
                data = normalize_activity(raw)
            except ValueError:
                logger.debug("Skipping unparseable activity: %s", raw.get("activityId"))
                continue

            existing = repo.get_activity_by_garmin_id(
                self.user.id, data["garmin_activity_id"]
            )
            raw_json = data.pop("raw_json", None)
            if existing:
                existing.name = data["name"]
                existing.start_time = data["start_time"]
                existing.garmin_type = data["garmin_type"]
                existing.suggested_category = data["suggested_category"]
                if existing.review_status != ReviewStatus.confirmed:
                    existing.category = data["suggested_category"]
                existing.distance_m = data["distance_m"]
                existing.elevation_gain_m = data["elevation_gain_m"]
                existing.duration_s = data["duration_s"]
                existing.active_calories = data["active_calories"]
                existing.calories = data["calories"]
                existing.avg_hr = data["avg_hr"]
                existing.max_hr = data["max_hr"]
                existing.synced_at = now
                existing.updated_at = now
                repo.put_activity(existing, raw_json=raw_json)
                if existing.review_status == ReviewStatus.confirmed:
                    touched.append(existing.start_time)
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
                    synced_at=now,
                    updated_at=now,
                )
                repo.put_activity(act, raw_json=raw_json)
                created += 1

        return created, updated, touched

    def _fail(
        self,
        run: SyncRun,
        message: str,
        garmin: GarminSession | None = None,
    ) -> SyncRun:
        run.status = SyncStatus.failed
        run.finished_at = utcnow()
        run.error = message
        repo.put_sync_run(run)
        if garmin:
            garmin.last_error = message
            repo.put_garmin(garmin)
        return run


def run_sync_job(user_id: str, run_id: str) -> None:
    user = repo.get_user(user_id)
    if not user:
        return
    SyncService(user).execute_sync(run_id)


def enqueue_sync(user_id: str, run_id: str) -> None:
    """Send SQS or run inline (call from a background thread locally)."""
    settings = get_settings()
    backend = (settings.sync_backend or "inline").lower()
    if backend == "sqs":
        if not settings.sync_queue_url:
            raise RuntimeError("SYNC_QUEUE_URL is required when SYNC_BACKEND=sqs")
        import boto3

        sqs = boto3.client("sqs", region_name=settings.aws_region)
        sqs.send_message(
            QueueUrl=settings.sync_queue_url,
            MessageBody=json.dumps({"user_id": user_id, "run_id": run_id}),
        )
        return
    run_sync_job(user_id, run_id)
