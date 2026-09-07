from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from garmin_tracker.main import app
from garmin_tracker.models import (
    Activity,
    ActivityCategory,
    GarminSession,
    ReviewStatus,
    ShareLink,
    SyncRun,
    SyncStatus,
)
from garmin_tracker.store import repo


def test_delete_all_data():
    email = f"wipe-me-{uuid4().hex}@example.com"
    share_token = f"wipe-token-{uuid4().hex}"
    with TestClient(app) as client:
        reg = client.post(
            "/api/auth/register",
            json={"email": email, "password": "password123"},
        )
        assert reg.status_code == 201, reg.text
        token = reg.json()["access_token"]
        user_id = reg.json()["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}

        repo.put_activity(
            Activity(
                user_id=user_id,
                garmin_activity_id="wipe-1",
                name="Run",
                start_time=datetime(2026, 1, 1, tzinfo=UTC),
                garmin_type="running",
                suggested_category=ActivityCategory.run,
                category=ActivityCategory.run,
                review_status=ReviewStatus.confirmed,
                distance_m=5000,
            )
        )
        repo.put_sync_run(
            SyncRun(
                user_id=user_id,
                status=SyncStatus.success,
                activities_fetched=1,
                activities_created=1,
            )
        )
        repo.put_share_link(ShareLink(user_id=user_id, token=share_token, label="Test"))
        repo.put_garmin(
            GarminSession(
                user_id=user_id,
                encrypted_token="fake-encrypted-token",
                garmin_email="garmin@example.com",
                last_success_at=datetime.now(UTC),
            )
        )

        res = client.delete("/api/account/data", headers=headers)
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["activities_deleted"] >= 1
        assert body["sync_runs_deleted"] >= 1
        assert "share_links_deleted" not in body
        assert "deleted" in body["message"].lower()

        assert repo.list_activities(user_id) == []
        assert repo.latest_sync_run(user_id) is None
        shares = repo.list_share_links(user_id)
        assert len(shares) == 1
        assert shares[0].token == share_token
        garmin = repo.get_garmin(user_id)
        assert garmin is not None
        assert garmin.garmin_email == "garmin@example.com"
        assert garmin.last_success_at is None

        listed = client.get("/api/share", headers=headers)
        assert listed.status_code == 200
        assert len(listed.json()) == 1

        status = client.get("/api/garmin/status", headers=headers)
        assert status.status_code == 200
        assert status.json()["connected"] is True

        me = client.get("/api/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["email"] == email


def test_delete_all_data_blocked_while_sync_running():
    email = f"wipe-busy-{uuid4().hex}@example.com"
    with TestClient(app) as client:
        reg = client.post(
            "/api/auth/register",
            json={"email": email, "password": "password123"},
        )
        assert reg.status_code == 201, reg.text
        token = reg.json()["access_token"]
        user_id = reg.json()["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}

        repo.put_sync_run(SyncRun(user_id=user_id, status=SyncStatus.running))

        res = client.delete("/api/account/data", headers=headers)
        assert res.status_code == 409
        assert "sync" in res.json()["detail"].lower()
