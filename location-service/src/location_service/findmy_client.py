"""Client abstraction over FindMy.py, decoupled from its object model.

`LocationPoint` is our own shape so the rest of the service (DB, API) never
touches FindMy.py types directly. `RealFindMyClient` adapts the real library;
`MockFindMyClient` (see mock_findmy.py) fabricates points for local dev and
tests without any Apple account.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from location_service.config import Settings


@dataclass(frozen=True)
class LocationPoint:
    timestamp: datetime
    latitude: float
    longitude: float
    confidence: int
    horizontal_accuracy: int
    status: int


class FindMyClient(Protocol):
    async def fetch_reports(self) -> list[LocationPoint]:
        """Fetch the known location history for Larry's AirTag."""
        ...


class RealFindMyClient:
    """Adapts findmy.AsyncAppleAccount + a KeyPair to the FindMyClient protocol."""

    def __init__(self, settings: Settings) -> None:
        if not settings.airtag_key_b64:
            msg = "FINDMY_AIRTAG_KEY_B64 must be set when FINDMY_MODE=live"
            raise ValueError(msg)
        self._settings = settings

    def _get_account(self):
        from findmy import AsyncAppleAccount

        store_path = Path(self._settings.account_store_path)
        if not store_path.exists():
            msg = (
                f"No saved Apple account session at {store_path}. "
                "Run the interactive login helper once (see README) before starting "
                "the service in live mode -- 2FA cannot be completed headlessly."
            )
            raise RuntimeError(msg)

        return AsyncAppleAccount.from_json(
            str(store_path), anisette_libs_path=self._settings.anisette_libs_path
        )

    async def fetch_reports(self) -> list[LocationPoint]:
        from findmy import KeyPair

        account = self._get_account()
        key = KeyPair.from_b64(self._settings.airtag_key_b64)

        try:
            reports = await account.fetch_location_history(key)
        finally:
            # Apple may rotate tokens during the request; always persist the
            # (possibly updated) session so the next poll doesn't re-auth.
            account.to_json(self._settings.account_store_path)

        return [
            LocationPoint(
                timestamp=r.timestamp,
                latitude=r.latitude,
                longitude=r.longitude,
                confidence=r.confidence,
                horizontal_accuracy=r.horizontal_accuracy,
                status=r.status,
            )
            for r in reports
        ]


def build_client(settings: Settings) -> FindMyClient:
    if settings.findmy_mode == "live":
        return RealFindMyClient(settings)

    from location_service.mock_findmy import MockAirTagState, MockFindMyClient

    # Wander around the configured home point, if any, so the mock and the
    # real round-trip detection (settings.home) never disagree about "home".
    state = MockAirTagState(*settings.home) if settings.home else None
    return MockFindMyClient(state=state)
