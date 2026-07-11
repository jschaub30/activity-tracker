from garmin_tracker.models import ActivityCategory
from garmin_tracker.services.activity_normalize import normalize_activity


def test_normalize_running_activity():
    raw = {
        "activityId": 12345,
        "activityName": "Morning Run",
        "startTimeGMT": "2026-07-01 14:00:00",
        "activityType": {"typeKey": "running"},
        "distance": 5000.0,
        "elevationGain": 50.0,
        "duration": 1800.0,
        "averageHR": 145,
        "maxHR": 170,
        "calories": 400,
    }
    data = normalize_activity(raw)
    assert data["garmin_activity_id"] == "12345"
    assert data["name"] == "Morning Run"
    assert data["garmin_type"] == "running"
    assert data["suggested_category"] == ActivityCategory.run
    assert data["distance_m"] == 5000.0
    assert data["elevation_gain_m"] == 50.0
    assert data["duration_s"] == 1800.0
    assert data["calories"] == 400.0


def test_normalize_walk_as_hike():
    raw = {
        "activityId": "99",
        "activityName": "Evening Walk",
        "startTimeGMT": "2026-07-02 01:00:00",
        "activityType": {"typeKey": "walking"},
        "distance": 3000,
        "elevationGain": 20,
        "duration": 2400,
    }
    data = normalize_activity(raw)
    assert data["suggested_category"] == ActivityCategory.hike


def test_normalize_stair_stepper():
    raw = {
        "activityId": 7,
        "activityName": "Stepper",
        "startTimeLocal": "2026-07-03 08:00:00",
        "activityType": {"typeKey": "stair_climbing"},
        "duration": 1200,
        "calories": 200,
        "elevationGain": 300,
    }
    data = normalize_activity(raw)
    assert data["suggested_category"] == ActivityCategory.stair
    assert data["calories"] == 200.0
