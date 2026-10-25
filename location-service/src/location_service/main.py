from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query

from location_service import db
from location_service.config import load_settings
from location_service.findmy_client import build_client
from location_service.poller import poll_forever
from location_service.trips import compute_trips, filter_quality, trip_to_dict

logging.basicConfig(level=logging.INFO)

settings = load_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db(settings.db_path)
    client = build_client(settings)
    task = asyncio.create_task(poll_forever(client, settings))
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(title="larry-tracker location-service", lifespan=lifespan)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "findmy_mode": settings.findmy_mode}


@app.get("/locations")
def list_locations(
    since: datetime | None = Query(default=None),
    limit: int = Query(default=1000, le=10000),
) -> list[dict]:
    return db.get_points(settings.db_path, since=since, limit=limit)


@app.get("/locations/latest")
def latest_location() -> dict:
    point = db.get_latest_point(settings.db_path)
    if point is None:
        raise HTTPException(status_code=404, detail="no locations recorded yet")
    return point


@app.get("/trips")
def list_trips(since: datetime | None = Query(default=None)) -> dict:
    points = db.get_points(settings.db_path, since=since, limit=100_000)
    points = filter_quality(
        points,
        min_confidence=settings.min_confidence,
        max_horizontal_accuracy_meters=settings.max_horizontal_accuracy_meters,
    )
    trips = compute_trips(
        points,
        gap_minutes=settings.trip_gap_minutes,
        home=settings.home,
        home_radius_meters=settings.home_radius_meters,
    )

    home = None
    if settings.home is not None:
        home = {
            "latitude": settings.home_latitude,
            "longitude": settings.home_longitude,
            "radius_meters": settings.home_radius_meters,
        }

    return {"home": home, "trips": [trip_to_dict(t) for t in trips]}
