"""moto DynamoDB for every test."""

from __future__ import annotations

import os

import pytest

os.environ["AWS_DEFAULT_REGION"] = "us-west-2"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SECURITY_TOKEN"] = "testing"
os.environ["AWS_SESSION_TOKEN"] = "testing"
os.environ["DYNAMODB_TABLE"] = "garmin-tracker-test"
os.environ["DYNAMODB_ENDPOINT"] = ""
os.environ["SYNC_BACKEND"] = "inline"
os.environ["ORIGIN_SECRET"] = ""


@pytest.fixture(autouse=True)
def ddb(monkeypatch):
    from moto import mock_aws

    from garmin_tracker.config import get_settings
    from garmin_tracker.store.client import ensure_table, reset_client

    monkeypatch.setenv("DYNAMODB_ENDPOINT", "")
    monkeypatch.setenv("DYNAMODB_TABLE", "garmin-tracker-test")
    monkeypatch.setenv("SYNC_BACKEND", "inline")
    monkeypatch.setenv("ORIGIN_SECRET", "")
    get_settings.cache_clear()
    reset_client()
    with mock_aws():
        reset_client()
        ensure_table()
        yield
        reset_client()
    get_settings.cache_clear()
