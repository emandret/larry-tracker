"""Splits raw location points into discrete journeys ("trips").

A trip boundary is a time gap between consecutive reports larger than
`gap_minutes` -- an AirTag dropping out of FindMy network coverage for a
while is the natural signal that an outing started or ended, independent of
how far Larry actually travelled. "Round trip" is a label computed on top
of that: whether a trip's last point ended back within `home_radius_meters`
of a configured home point. It is deliberately not the segmentation rule
itself -- GPS/BLE positions never land on the exact same point twice, and a
cat that spends the whole day near home would otherwise look like dozens of
trips.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

EARTH_RADIUS_METERS = 6_371_000


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in meters."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_METERS * math.asin(math.sqrt(a))


def filter_quality(
    points: list[dict],
    min_confidence: int,
    max_horizontal_accuracy_meters: float,
) -> list[dict]:
    """Drop points too unreliable to be worth plotting or segmenting on."""
    return [
        p
        for p in points
        if p["confidence"] >= min_confidence
        and p["horizontal_accuracy"] <= max_horizontal_accuracy_meters
    ]


@dataclass(frozen=True)
class Trip:
    points: list[dict]
    is_round_trip: bool | None  # None when no home point is configured


def compute_trips(
    points: list[dict],
    gap_minutes: float,
    home: tuple[float, float] | None,
    home_radius_meters: float,
) -> list[Trip]:
    """Group time-ordered points into trips, split wherever points are more
    than `gap_minutes` apart."""
    if not points:
        return []

    gap = timedelta(minutes=gap_minutes)
    groups: list[list[dict]] = [[points[0]]]

    for prev, curr in zip(points, points[1:]):
        prev_ts = datetime.fromisoformat(prev["timestamp"])
        curr_ts = datetime.fromisoformat(curr["timestamp"])
        if curr_ts - prev_ts > gap:
            groups.append([])
        groups[-1].append(curr)

    trips = []
    for group in groups:
        is_round_trip = None
        if home is not None:
            last = group[-1]
            distance = haversine_meters(last["latitude"], last["longitude"], *home)
            is_round_trip = distance <= home_radius_meters
        trips.append(Trip(points=group, is_round_trip=is_round_trip))

    return trips


def trip_to_dict(trip: Trip) -> dict:
    start = trip.points[0]["timestamp"]
    end = trip.points[-1]["timestamp"]
    duration_minutes = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds() / 60

    return {
        "start": start,
        "end": end,
        "duration_minutes": round(duration_minutes, 1),
        "point_count": len(trip.points),
        "is_round_trip": trip.is_round_trip,
        "points": trip.points,
    }
