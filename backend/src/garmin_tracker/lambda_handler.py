"""Lambda entry for the FastAPI API (Mangum)."""

from mangum import Mangum

from garmin_tracker.main import app

handler = Mangum(app, lifespan="off")
