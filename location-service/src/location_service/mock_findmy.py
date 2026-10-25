"""Mock FindMy client for local dev and tests -- no Apple account required.

Deliberately built from plain dataclasses you construct directly (rather than
`unittest.mock`), so it can double as example data for the DB and UI layers.
Each call to `fetch_reports` nudges a simulated AirTag a little further along
a random walk, so repeated polling produces a plausible-looking path.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timezone

from location_service.findmy_client import LocationPoint


@dataclass(frozen=True)
class MockAirTagState:
    """Starting point and wander radius for the simulated walk."""

    home_latitude: float = 51.513487  # E14 6GT, Canary Wharf
    home_longitude: float = -0.020869
    wander_radius_deg: float = 0.0015  # roughly 150m at this latitude


class MockFindMyClient:
    def __init__(self, state: MockAirTagState | None = None, seed: int | None = None) -> None:
        self._state = state or MockAirTagState()
        self._rng = random.Random(seed)
        self._lat = self._state.home_latitude
        self._lon = self._state.home_longitude

    async def fetch_reports(self) -> list[LocationPoint]:
        now = datetime.now(timezone.utc)
        points: list[LocationPoint] = []

        for _ in range(self._rng.randint(1, 3)):
            self._lat += self._rng.uniform(-1, 1) * self._state.wander_radius_deg
            self._lon += self._rng.uniform(-1, 1) * self._state.wander_radius_deg
            points.append(
                LocationPoint(
                    timestamp=now,
                    latitude=self._lat,
                    longitude=self._lon,
                    confidence=self._rng.randint(1, 3),
                    horizontal_accuracy=self._rng.randint(5, 25),
                    status=0,
                )
            )

        return points
