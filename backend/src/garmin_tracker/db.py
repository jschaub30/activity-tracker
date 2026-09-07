from garmin_tracker.config import get_settings
from garmin_tracker.store.client import ensure_table, reset_client


def init_db() -> None:
    """Create the table when talking to DynamoDB Local / moto."""
    settings = get_settings()
    if settings.dynamodb_endpoint:
        ensure_table()


def reset_db_client() -> None:
    reset_client()
