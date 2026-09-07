"""SQS / Lambda worker for Garmin sync chunks."""

from __future__ import annotations

import json
import logging

from garmin_tracker.models import SyncStatus
from garmin_tracker.services.sync_service import SyncService, enqueue_sync
from garmin_tracker.store import repo

logger = logging.getLogger(__name__)


def process_message(body: dict) -> None:
    action = body.get("action")
    if action == "sync_all":
        for user_id in repo.list_profile_user_ids():
            user = repo.get_user(user_id)
            if not user:
                continue
            svc = SyncService(user)
            if svc.is_running() or not svc.garmin_row():
                continue
            try:
                run = svc.create_running_sync()
                enqueue_sync(user.id, run.id)
            except Exception:  # noqa: BLE001
                logger.exception("Could not enqueue sync for %s", user_id)
        return

    user_id = body["user_id"]
    run_id = body["run_id"]
    user = repo.get_user(user_id)
    if not user:
        logger.warning("sync worker: user %s not found", user_id)
        return
    svc = SyncService(user)
    run = svc.execute_chunk(run_id)
    if run.status == SyncStatus.running:
        enqueue_sync(user_id, run_id)


def handler(event: dict, _context: object) -> dict:
    records = event.get("Records") or []
    if not records and event.get("user_id"):
        process_message(event)
        return {"ok": True}
    for record in records:
        body = json.loads(record["body"])
        process_message(body)
    return {"ok": True}
