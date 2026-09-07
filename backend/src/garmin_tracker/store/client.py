"""DynamoDB table client, serdes, and local table bootstrap."""

from __future__ import annotations

from contextlib import suppress
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

import boto3
from botocore.exceptions import ClientError

from garmin_tracker.config import get_settings

_TABLE = None
_RESOURCE = None


def reset_client() -> None:
    """Drop cached resource (tests)."""
    global _TABLE, _RESOURCE
    _TABLE = None
    _RESOURCE = None


def _session_kwargs() -> dict[str, Any]:
    settings = get_settings()
    kwargs: dict[str, Any] = {"region_name": settings.aws_region}
    if settings.dynamodb_endpoint:
        kwargs["endpoint_url"] = settings.dynamodb_endpoint
    return kwargs


def dynamodb_resource():
    global _RESOURCE
    if _RESOURCE is None:
        _RESOURCE = boto3.resource("dynamodb", **_session_kwargs())
    return _RESOURCE


def dynamodb_client():
    return boto3.client("dynamodb", **_session_kwargs())


def table():
    global _TABLE
    if _TABLE is None:
        _TABLE = dynamodb_resource().Table(get_settings().dynamodb_table)
    return _TABLE


def to_ddb(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: to_ddb(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [to_ddb(v) for v in value]
    return value


def from_ddb(value: Any) -> Any:
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)
    if isinstance(value, dict):
        return {k: from_ddb(v) for k, v in value.items()}
    if isinstance(value, list):
        return [from_ddb(v) for v in value]
    return value


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def query_all(**kwargs) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    while True:
        resp = table().query(**kwargs)
        items.extend(resp.get("Items") or [])
        lek = resp.get("LastEvaluatedKey")
        if not lek:
            break
        kwargs["ExclusiveStartKey"] = lek
    return [from_ddb(i) for i in items]


def batch_delete(keys: list[dict[str, str]]) -> None:
    tbl = table()
    for i in range(0, len(keys), 25):
        chunk = keys[i : i + 25]
        with tbl.batch_writer() as batch:
            for key in chunk:
                batch.delete_item(Key=key)


def ensure_table() -> None:
    """Create the single table when using DynamoDB Local / moto."""
    settings = get_settings()
    client = dynamodb_client()
    try:
        client.describe_table(TableName=settings.dynamodb_table)
        return
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ResourceNotFoundException":
            raise
    client.create_table(
        TableName=settings.dynamodb_table,
        KeySchema=[
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    client.get_waiter("table_exists").wait(TableName=settings.dynamodb_table)
    with suppress(ClientError):
        client.update_time_to_live(
            TableName=settings.dynamodb_table,
            TimeToLiveSpecification={"Enabled": True, "AttributeName": "ttl"},
        )
