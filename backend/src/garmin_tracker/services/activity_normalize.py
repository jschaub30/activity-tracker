"""Normalize Garmin Connect activity JSON into our Activity fields."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from garmin_tracker.categorization import suggest_category
from garmin_tracker.models import ActivityCategory


def _nested_type_key(raw: dict[str, Any]) -> str:
    at = raw.get("activityType") or raw.get("activityTypeDTO") or {}
    if isinstance(at, dict):
        return str(
            at.get("typeKey")
            or at.get("typeKeyDTO")
            or at.get("key")
            or at.get("typeId")
            or ""
        )
    if isinstance(at, str):
        return at
    return str(raw.get("activityTypeKey") or raw.get("typeKey") or "")


def _parse_start_time(raw: dict[str, Any]) -> datetime:
    for key in ("startTimeGMT", "startTimeLocal", "beginTimestamp", "startTime"):
        val = raw.get(key)
        if val is None:
            continue
        if isinstance(val, (int, float)):
            # ms vs s
            ts = float(val)
            if ts > 1e12:
                ts /= 1000.0
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        if isinstance(val, str):
            s = val.strip()
            # "2024-01-15 12:34:56" or ISO
            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
            ):
                try:
                    dt = datetime.strptime(s.replace("Z", ""), fmt.replace("Z", ""))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except ValueError:
                    continue
            try:
                dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
    return datetime.now(timezone.utc)


def _num(raw: dict[str, Any], *keys: str) -> float | None:
    for k in keys:
        if k not in raw or raw[k] is None:
            continue
        try:
            return float(raw[k])
        except (TypeError, ValueError):
            continue
    return None


def normalize_activity(raw: dict[str, Any]) -> dict[str, Any]:
    """Return dict of fields for Activity model (excluding user_id / ids management)."""
    aid = raw.get("activityId") or raw.get("activityIdStr") or raw.get("activityUUID")
    if aid is None:
        raise ValueError("Activity missing activityId")

    garmin_type = _nested_type_key(raw)
    suggested = suggest_category(garmin_type)

    distance = _num(raw, "distance", "distanceInMeters")
    elev = _num(raw, "elevationGain", "elevationGainInMeters", "totalElevationGain")
    duration = _num(raw, "duration", "elapsedDuration", "movingDuration")
    # Garmin Connect exposes "calories" (not "active calories") as the main field
    calories = _num(raw, "calories", "Calories", "totalCalories")
    active_cal = _num(raw, "activeCalories", "active_calories")
    if calories is None and active_cal is not None:
        calories = active_cal
    avg_hr = _num(raw, "averageHR", "avgHR", "averageHeartRate")
    max_hr = _num(raw, "maxHR", "maxHeartRate")

    name = str(raw.get("activityName") or raw.get("name") or garmin_type or "Activity")

    # Keep a compact raw snapshot (avoid huge payloads)
    try:
        raw_json = json.dumps(raw, default=str)[:50_000]
    except (TypeError, ValueError):
        raw_json = None

    return {
        "garmin_activity_id": str(aid),
        "name": name,
        "start_time": _parse_start_time(raw),
        "garmin_type": garmin_type,
        "suggested_category": suggested,
        "distance_m": distance,
        "elevation_gain_m": elev,
        "duration_s": duration,
        "active_calories": active_cal,
        "calories": calories,
        "avg_hr": avg_hr,
        "max_hr": max_hr,
        "raw_json": raw_json,
    }


def default_category_for_new(suggested: ActivityCategory) -> ActivityCategory:
    return suggested
