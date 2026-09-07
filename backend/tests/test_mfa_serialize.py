import json

from garmin_tracker.services.garmin_client import (
    GarminClientError,
    deserialize_pending_mfa,
    serialize_pending_mfa,
)


class _FakeClient:
    """Stand-in for a mid-MFA Garmin object (pickle path)."""

    def __init__(self, email: str):
        self.email = email
        self.flag = "pending-mfa"


def test_pickle_pending_mfa_round_trip():
    original = _FakeClient("a@example.com")
    blob = serialize_pending_mfa(original, "a@example.com")  # type: ignore[arg-type]
    payload = json.loads(blob)
    assert payload["kind"] == "pickle"
    client, email = deserialize_pending_mfa(blob)
    assert email == "a@example.com"
    assert client.email == "a@example.com"
    assert client.flag == "pending-mfa"


def test_unknown_kind_raises():
    blob = json.dumps({"kind": "unknown", "email": "x@y.z"})
    try:
        deserialize_pending_mfa(blob)
        raise AssertionError("expected GarminClientError")
    except GarminClientError as exc:
        assert "Unrecognized" in str(exc)
