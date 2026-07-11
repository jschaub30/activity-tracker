from garmin_tracker.categorization import suggest_category
from garmin_tracker.models import ActivityCategory


def test_walk_maps_to_hike():
    assert suggest_category("walking") == ActivityCategory.hike
    assert suggest_category("hiking") == ActivityCategory.hike


def test_running_maps_to_run():
    assert suggest_category("running") == ActivityCategory.run
    assert suggest_category("trail_running") == ActivityCategory.run


def test_stair_stepper_maps_to_stair():
    assert suggest_category("stair_climbing") == ActivityCategory.stair
    assert suggest_category("stair_stepper") == ActivityCategory.stair
    assert suggest_category("stepper") == ActivityCategory.stair


def test_strength_and_cardio():
    assert suggest_category("strength_training") == ActivityCategory.strength
    assert suggest_category("indoor_cardio") == ActivityCategory.cardio
    # Stairs are not cardio
    assert suggest_category("stair_climbing") != ActivityCategory.cardio
