from __future__ import annotations

import asyncio
import logging
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from location_service import db
from location_service.config import load_settings
from location_service.findmy_client import build_client
from location_service.poller import poll_forever
from location_service.trips import compute_trips, filter_quality, trip_to_dict
from location_service.ws import Broadcaster

logging.basicConfig(level=logging.INFO)

settings = load_settings()
broadcaster = Broadcaster()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db(settings.db_path)
    client = build_client(settings)
    task = asyncio.create_task(
        poll_forever(
            client,
            settings,
            on_update=lambda: broadcaster.broadcast({"type": "locations_updated"}),
        )
    )
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(title="larry-tracker location-service", lifespan=lifespan)


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    """Clients connect and get a `{"type": "locations_updated"}` message
    whenever the poller or a manual edit changes stored data -- a signal to
    refetch /trips, not a stream of the data itself."""
    await broadcaster.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # we don't expect messages; just detect disconnects
    except WebSocketDisconnect:
        broadcaster.disconnect(websocket)


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


class LocationUpdate(BaseModel):
    """All fields optional: a PATCH only changes what it includes."""

    timestamp: datetime | None = None
    latitude: float | None = None
    longitude: float | None = None
    confidence: int | None = None
    horizontal_accuracy: int | None = None
    status: int | None = None


@app.patch("/locations/{point_id}")
async def update_location(point_id: int, body: LocationUpdate) -> dict:
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="no fields to update")
    if "timestamp" in fields:
        fields["timestamp"] = body.timestamp.isoformat()

    try:
        changed = db.update_point(settings.db_path, point_id, fields)
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409, detail="another point already has that timestamp and position"
        ) from None

    if not changed:
        raise HTTPException(status_code=404, detail="point not found")

    await broadcaster.broadcast({"type": "locations_updated"})
    return db.get_point(settings.db_path, point_id)


@app.delete("/locations/{point_id}", status_code=204)
async def delete_location(point_id: int) -> Response:
    if not db.delete_point(settings.db_path, point_id):
        raise HTTPException(status_code=404, detail="point not found")

    await broadcaster.broadcast({"type": "locations_updated"})
    return Response(status_code=204)


class BulkDeleteRequest(BaseModel):
    ids: list[int]


@app.post("/locations/bulk-delete")
async def bulk_delete_locations(body: BulkDeleteRequest) -> dict:
    """Delete several points at once -- e.g. an entire trip, identified by
    the UI from the point ids it already has loaded from /trips."""
    deleted = db.delete_points(settings.db_path, body.ids)

    if deleted:
        await broadcaster.broadcast({"type": "locations_updated"})

    return {"deleted": deleted}


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
