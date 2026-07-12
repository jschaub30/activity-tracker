from fastapi.testclient import TestClient

from garmin_tracker.main import app


def test_share_link_public_weeks():
    with TestClient(app) as client:
        reg = client.post(
            "/api/auth/register",
            json={"email": "share-owner@example.com", "password": "password123"},
        )
        assert reg.status_code == 201, reg.text
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        created = client.post(
            "/api/share",
            headers=headers,
            json={"label": "Friends"},
        )
        assert created.status_code == 201, created.text
        share = created.json()
        assert share["label"] == "Friends"
        assert share["path"].startswith("/s/")
        share_token = share["token"]

        meta = client.get(f"/api/public/{share_token}")
        assert meta.status_code == 200, meta.text
        assert meta.json()["owner_display"] == "share-owner"

        weeks = client.get(f"/api/public/{share_token}/weeks?count=4")
        assert weeks.status_code == 200, weeks.text
        assert len(weeks.json()["weeks"]) == 4

        # No auth required for public
        listed = client.get("/api/share", headers=headers)
        assert listed.status_code == 200
        assert len(listed.json()) == 1

        rev = client.delete(f"/api/share/{share['id']}", headers=headers)
        assert rev.status_code == 204

        gone = client.get(f"/api/public/{share_token}/weeks")
        assert gone.status_code == 404
