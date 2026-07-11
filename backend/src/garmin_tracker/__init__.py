"""Garmin Tracker API."""

__version__ = "0.1.0"


def main() -> None:
    import uvicorn

    uvicorn.run(
        "garmin_tracker.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
