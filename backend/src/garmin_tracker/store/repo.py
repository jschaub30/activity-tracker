"""Single-table DynamoDB repository."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

from garmin_tracker.config import get_settings
from garmin_tracker.models import (
    Activity,
    ActivityCategory,
    DisplayUnits,
    GarminSession,
    ReviewStatus,
    ShareLink,
    SyncRun,
    SyncStatus,
    User,
    utcnow,
)
from garmin_tracker.store.client import (
    batch_delete,
    from_ddb,
    parse_dt,
    query_all,
    table,
    to_ddb,
)
from garmin_tracker.store.keys import (
    act_sk_prefix,
    email_pk,
    share_pk,
    share_sk_prefix,
    sk_act,
    sk_aid,
    sk_garmin,
    sk_gid,
    sk_mfa,
    sk_profile,
    sk_share,
    sk_sync,
    sk_synid,
    sk_week,
    sync_sk_prefix,
    user_pk,
)


def _get(pk: str, sk: str) -> dict[str, Any] | None:
    item = table().get_item(
        Key={"pk": pk, "sk": sk}, ConsistentRead=True
    ).get("Item")
    return from_ddb(item) if item else None

MFA_TTL_SECONDS = 10 * 60


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _user_from_item(item: dict[str, Any]) -> User:
    return User(
        id=item["id"],
        email=item["email"],
        password_hash=item["password_hash"],
        timezone=item.get("timezone") or "America/Denver",
        units=DisplayUnits(item.get("units") or DisplayUnits.imperial),
        created_at=parse_dt(item.get("created_at")) or utcnow(),
    )


def _garmin_from_item(item: dict[str, Any]) -> GarminSession:
    return GarminSession(
        id=item.get("id") or item["user_id"],
        user_id=item["user_id"],
        encrypted_token=item["encrypted_token"],
        garmin_email=item.get("garmin_email"),
        connected_at=parse_dt(item.get("connected_at")) or utcnow(),
        last_success_at=parse_dt(item.get("last_success_at")),
        last_error=item.get("last_error"),
        history_complete=bool(item.get("history_complete")),
    )


def _activity_from_item(item: dict[str, Any]) -> Activity:
    return Activity(
        id=item["id"],
        user_id=item["user_id"],
        garmin_activity_id=item["garmin_activity_id"],
        name=item.get("name") or "",
        start_time=parse_dt(item.get("start_time")) or utcnow(),
        garmin_type=item.get("garmin_type") or "",
        suggested_category=ActivityCategory(
            item.get("suggested_category") or "uncategorized"
        ),
        category=ActivityCategory(item.get("category") or "uncategorized"),
        review_status=ReviewStatus(item.get("review_status") or "confirmed"),
        distance_m=item.get("distance_m"),
        elevation_gain_m=item.get("elevation_gain_m"),
        duration_s=item.get("duration_s"),
        active_calories=item.get("active_calories"),
        avg_hr=item.get("avg_hr"),
        max_hr=item.get("max_hr"),
        calories=item.get("calories"),
        synced_at=parse_dt(item.get("synced_at")) or utcnow(),
        updated_at=parse_dt(item.get("updated_at")) or utcnow(),
    )


def _sync_from_item(item: dict[str, Any]) -> SyncRun:
    return SyncRun(
        id=item["id"],
        user_id=item["user_id"],
        status=SyncStatus(item.get("status") or "running"),
        started_at=parse_dt(item.get("started_at")) or utcnow(),
        finished_at=parse_dt(item.get("finished_at")),
        range_start=parse_dt(item.get("range_start")),
        range_end=parse_dt(item.get("range_end")),
        activities_fetched=int(item.get("activities_fetched") or 0),
        activities_created=int(item.get("activities_created") or 0),
        activities_updated=int(item.get("activities_updated") or 0),
        error=item.get("error"),
        cursor=item.get("cursor"),
        updated_at=parse_dt(item.get("updated_at"))
        or parse_dt(item.get("started_at"))
        or utcnow(),
    )


def _share_from_item(item: dict[str, Any]) -> ShareLink:
    return ShareLink(
        id=item["id"],
        user_id=item["user_id"],
        token=item["token"],
        label=item.get("label"),
        created_at=parse_dt(item.get("created_at")) or utcnow(),
        revoked_at=parse_dt(item.get("revoked_at")),
    )


def get_user(user_id: str) -> User | None:
    item = _get(user_pk(user_id), sk_profile())
    return _user_from_item(item) if item else None


def get_user_by_email(email: str) -> User | None:
    item = _get(email_pk(email), "USER")
    if not item:
        return None
    return get_user(item["user_id"])


def create_user(user: User) -> User:
    tbl = table()
    try:
        tbl.put_item(
            Item=to_ddb(
                {
                    "pk": email_pk(user.email),
                    "sk": "USER",
                    "user_id": user.id,
                    "email": user.email,
                }
            ),
            ConditionExpression="attribute_not_exists(pk)",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ValueError("Email already registered") from exc
        raise
    return put_user(user)


def put_user(user: User) -> User:
    table().put_item(
        Item=to_ddb(
            {
                "pk": user_pk(user.id),
                "sk": sk_profile(),
                "id": user.id,
                "email": user.email,
                "password_hash": user.password_hash,
                "timezone": user.timezone,
                "units": user.units,
                "created_at": user.created_at,
            }
        )
    )
    return user


def get_garmin(user_id: str) -> GarminSession | None:
    item = _get(user_pk(user_id), sk_garmin())
    return _garmin_from_item(item) if item else None


def put_garmin(row: GarminSession) -> GarminSession:
    table().put_item(
        Item=to_ddb(
            {
                "pk": user_pk(row.user_id),
                "sk": sk_garmin(),
                "id": row.id,
                "user_id": row.user_id,
                "encrypted_token": row.encrypted_token,
                "garmin_email": row.garmin_email,
                "connected_at": row.connected_at,
                "last_success_at": row.last_success_at,
                "last_error": row.last_error,
                "history_complete": row.history_complete,
            }
        )
    )
    return row


def delete_garmin(user_id: str) -> None:
    table().delete_item(Key={"pk": user_pk(user_id), "sk": sk_garmin()})


def put_mfa(user_id: str, blob: str) -> None:
    expires = int(utcnow().timestamp()) + MFA_TTL_SECONDS
    table().put_item(
        Item={
            "pk": user_pk(user_id),
            "sk": sk_mfa(),
            "blob": blob,
            "ttl": expires,
        }
    )


def get_mfa(user_id: str) -> str | None:
    item = _get(user_pk(user_id), sk_mfa())
    if not item:
        return None
    return item.get("blob")


def delete_mfa(user_id: str) -> None:
    table().delete_item(Key={"pk": user_pk(user_id), "sk": sk_mfa()})


def _put_raw_json(user_id: str, garmin_id: str, raw_json: str | None) -> None:
    bucket = get_settings().data_bucket
    if not bucket or not raw_json:
        return
    import boto3

    s3 = boto3.client("s3", region_name=get_settings().aws_region)
    s3.put_object(
        Bucket=bucket,
        Key=f"{user_id}/{garmin_id}.json",
        Body=raw_json.encode("utf-8"),
        ContentType="application/json",
    )


def get_activity(user_id: str, activity_id: str) -> Activity | None:
    ptr = _get(user_pk(user_id), sk_aid(activity_id))
    if not ptr:
        return None
    item = _get(user_pk(user_id), sk_act(ptr["start_iso"], ptr["garmin_activity_id"]))
    return _activity_from_item(item) if item else None


def get_activity_by_garmin_id(user_id: str, garmin_id: str) -> Activity | None:
    ptr = _get(user_pk(user_id), sk_gid(garmin_id))
    if not ptr:
        return None
    item = _get(user_pk(user_id), sk_act(ptr["start_iso"], garmin_id))
    return _activity_from_item(item) if item else None


def put_activity(act: Activity, raw_json: str | None = None) -> Activity:
    """Write activity + GID/AID pointers. Replaces ACT item if start_time changed."""
    start_iso = _iso(act.start_time)
    pk = user_pk(act.user_id)
    old_gid = _get(pk, sk_gid(act.garmin_activity_id))
    tbl = table()
    if old_gid and old_gid.get("start_iso") and old_gid["start_iso"] != start_iso:
        tbl.delete_item(
            Key={"pk": pk, "sk": sk_act(old_gid["start_iso"], act.garmin_activity_id)}
        )
    item = {
        "pk": pk,
        "sk": sk_act(start_iso, act.garmin_activity_id),
        "id": act.id,
        "user_id": act.user_id,
        "garmin_activity_id": act.garmin_activity_id,
        "name": act.name,
        "start_time": act.start_time,
        "garmin_type": act.garmin_type,
        "suggested_category": act.suggested_category,
        "category": act.category,
        "review_status": act.review_status,
        "distance_m": act.distance_m,
        "elevation_gain_m": act.elevation_gain_m,
        "duration_s": act.duration_s,
        "active_calories": act.active_calories,
        "avg_hr": act.avg_hr,
        "max_hr": act.max_hr,
        "calories": act.calories,
        "synced_at": act.synced_at,
        "updated_at": act.updated_at,
    }
    tbl.put_item(Item=to_ddb(item))
    tbl.put_item(
        Item={
            "pk": pk,
            "sk": sk_gid(act.garmin_activity_id),
            "start_iso": start_iso,
            "activity_id": act.id,
            "garmin_activity_id": act.garmin_activity_id,
        }
    )
    tbl.put_item(
        Item={
            "pk": pk,
            "sk": sk_aid(act.id),
            "start_iso": start_iso,
            "garmin_activity_id": act.garmin_activity_id,
            "activity_id": act.id,
        }
    )
    _put_raw_json(act.user_id, act.garmin_activity_id, raw_json)
    return act


def list_activities(
    user_id: str,
    *,
    start_iso: str | None = None,
    end_iso: str | None = None,
) -> list[Activity]:
    pk = user_pk(user_id)
    if start_iso and end_iso:
        cond = Key("pk").eq(pk) & Key("sk").between(
            f"ACT#{start_iso}",
            f"ACT#{end_iso}\uffff",
        )
    else:
        cond = Key("pk").eq(pk) & Key("sk").begins_with(act_sk_prefix())
    items = query_all(KeyConditionExpression=cond)
    return [
        _activity_from_item(i)
        for i in items
        if i.get("sk", "").startswith("ACT#") and "id" in i
    ]


def has_activities(user_id: str) -> bool:
    resp = table().query(
        KeyConditionExpression=Key("pk").eq(user_pk(user_id))
        & Key("sk").begins_with(act_sk_prefix()),
        Limit=1,
    )
    return bool(resp.get("Items"))


def put_week(user_id: str, sunday: str, payload: dict[str, Any]) -> None:
    table().put_item(
        Item=to_ddb(
            {
                "pk": user_pk(user_id),
                "sk": sk_week(sunday),
                "week_start": sunday,
                "payload": json.dumps(payload),
            }
        )
    )


def get_week(user_id: str, sunday: str) -> dict[str, Any] | None:
    item = _get(user_pk(user_id), sk_week(sunday))
    if not item or not item.get("payload"):
        return None
    raw = item["payload"]
    return json.loads(raw) if isinstance(raw, str) else raw


def put_sync_run(run: SyncRun) -> SyncRun:
    started_iso = _iso(run.started_at)
    pk = user_pk(run.user_id)
    tbl = table()
    tbl.put_item(
        Item=to_ddb(
            {
                "pk": pk,
                "sk": sk_sync(started_iso, run.id),
                "id": run.id,
                "user_id": run.user_id,
                "status": run.status,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "range_start": run.range_start,
                "range_end": run.range_end,
                "activities_fetched": run.activities_fetched,
                "activities_created": run.activities_created,
                "activities_updated": run.activities_updated,
                "error": run.error,
                "cursor": run.cursor,
                "updated_at": run.updated_at,
            }
        )
    )
    tbl.put_item(
        Item={
            "pk": pk,
            "sk": sk_synid(run.id),
            "started_iso": started_iso,
            "id": run.id,
        }
    )
    return run


def get_sync_run(user_id: str, run_id: str) -> SyncRun | None:
    ptr = _get(user_pk(user_id), sk_synid(run_id))
    if not ptr:
        return None
    item = _get(user_pk(user_id), sk_sync(ptr["started_iso"], run_id))
    return _sync_from_item(item) if item else None


def latest_sync_run(user_id: str) -> SyncRun | None:
    resp = table().query(
        KeyConditionExpression=Key("pk").eq(user_pk(user_id))
        & Key("sk").begins_with(sync_sk_prefix()),
        ScanIndexForward=False,
        Limit=8,
    )
    for raw in resp.get("Items") or []:
        item = from_ddb(raw)
        if item.get("sk", "").startswith("SYNC#") and "status" in item:
            return _sync_from_item(item)
    return None


def list_running_syncs(user_id: str) -> list[SyncRun]:
    items = query_all(
        KeyConditionExpression=Key("pk").eq(user_pk(user_id))
        & Key("sk").begins_with(sync_sk_prefix()),
        FilterExpression=Attr("status").eq("running"),
    )
    return [
        _sync_from_item(i)
        for i in items
        if i.get("sk", "").startswith("SYNC#") and i.get("status") == "running"
    ]


def is_sync_running(user_id: str, *, stale_after_seconds: int | None = None) -> bool:
    now = utcnow()
    for run in list_running_syncs(user_id):
        if stale_after_seconds is not None:
            ts = run.updated_at or run.started_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            if (now - ts).total_seconds() > stale_after_seconds:
                continue
        return True
    return False


def list_share_links(user_id: str) -> list[ShareLink]:
    items = query_all(
        KeyConditionExpression=Key("pk").eq(user_pk(user_id))
        & Key("sk").begins_with(share_sk_prefix())
    )
    links = [_share_from_item(i) for i in items if "token" in i]
    links.sort(key=lambda s: s.created_at, reverse=True)
    return links


def put_share_link(link: ShareLink) -> ShareLink:
    tbl = table()
    body = to_ddb(
        {
            "id": link.id,
            "user_id": link.user_id,
            "token": link.token,
            "label": link.label,
            "created_at": link.created_at,
            "revoked_at": link.revoked_at,
        }
    )
    tbl.put_item(Item={"pk": user_pk(link.user_id), "sk": sk_share(link.token), **body})
    tbl.put_item(Item={"pk": share_pk(link.token), "sk": "META", **body})
    return link


def get_share_by_token(token: str) -> ShareLink | None:
    item = _get(share_pk(token), "META")
    return _share_from_item(item) if item else None


def get_share_by_id(user_id: str, link_id: str) -> ShareLink | None:
    for link in list_share_links(user_id):
        if link.id == link_id:
            return link
    return None


def wipe_activity_data(user_id: str) -> tuple[int, int]:
    """Delete ACT/GID/AID/WEEK/SYNC items. Keep profile, garmin tokens, shares."""
    pk = user_pk(user_id)
    items = query_all(KeyConditionExpression=Key("pk").eq(pk))
    act_n = 0
    sync_n = 0
    keys: list[dict[str, str]] = []
    for item in items:
        sk = item.get("sk") or ""
        if sk.startswith("ACT#") and item.get("id"):
            act_n += 1
        if sk.startswith("SYNC#") and item.get("status"):
            sync_n += 1
        if (
            sk.startswith("ACT#")
            or sk.startswith("GID#")
            or sk.startswith("AID#")
            or sk.startswith("WEEK#")
            or sk.startswith("SYNC#")
            or sk.startswith("SYNID#")
        ):
            keys.append({"pk": pk, "sk": sk})
    batch_delete(keys)
    garmin = get_garmin(user_id)
    if garmin:
        garmin.last_success_at = None
        garmin.last_error = None
        garmin.history_complete = False
        put_garmin(garmin)
    return act_n, sync_n


def list_profile_user_ids() -> list[str]:
    """Scan PROFILE items (scheduled sync). Fine at personal scale."""
    tbl = table()
    user_ids: list[str] = []
    kwargs: dict[str, Any] = {
        "FilterExpression": Attr("sk").eq(sk_profile()),
        "ProjectionExpression": "id",
    }
    while True:
        resp = tbl.scan(**kwargs)
        for item in resp.get("Items") or []:
            if item.get("id"):
                user_ids.append(item["id"])
        lek = resp.get("LastEvaluatedKey")
        if not lek:
            break
        kwargs["ExclusiveStartKey"] = lek
    return user_ids
