"""Map Garmin activity types to app categories.

Walks default to hike (user can re-label on review).
Stair stepper / stair climbing → stair (included in week summary with runs & hikes).
"""

from garmin_tracker.models import ActivityCategory

_RUN_KEYS = {
    "running",
    "trail_running",
    "treadmill_running",
    "track_running",
    "indoor_running",
    "street_running",
    "ultra_run",
    "virtual_run",
}

_HIKE_KEYS = {
    "walking",
    "hiking",
    "casual_walking",
    "speed_walking",
    "trail_walking",
    "mountaineering",
}

_STAIR_KEYS = {
    "stair_climbing",
    "stair_stepper",
    "stairs",
    "stepper",
    "stairmaster",
}

_STRENGTH_KEYS = {
    "strength_training",
}

_CARDIO_KEYS = {
    "cardio",
    "indoor_cardio",
    "elliptical",
    "rowing",
    "indoor_rowing",
    "hiit",
    "yoga",
    "pilates",
    "breathwork",
    "meditation",
    "fitness_equipment",
}


def suggest_category(garmin_type: str | None) -> ActivityCategory:
    if not garmin_type:
        return ActivityCategory.uncategorized

    key = garmin_type.strip().lower().replace(" ", "_").replace("-", "_")

    if key in _RUN_KEYS or "run" in key:
        return ActivityCategory.run
    if key in _HIKE_KEYS or key in {"walk", "hike"} or "walk" in key or "hik" in key:
        return ActivityCategory.hike
    if (
        key in _STAIR_KEYS
        or "stair" in key
        or "stepper" in key
        or key.endswith("_stairs")
    ):
        return ActivityCategory.stair
    if key in _STRENGTH_KEYS or "strength" in key:
        return ActivityCategory.strength
    if key in _CARDIO_KEYS or "cardio" in key or "elliptical" in key:
        return ActivityCategory.cardio

    return ActivityCategory.uncategorized
