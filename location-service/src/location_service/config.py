"""Environment-based configuration. No framework needed for this few settings."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    findmy_mode: str  # "mock" or "live"
    db_path: str
    poll_interval_seconds: int
    account_store_path: str
    anisette_libs_path: str
    anisette_server_url: str | None
    airtag_key_b64: str | None

    # Trip segmentation (see trips.py).
    trip_gap_minutes: float
    home_latitude: float | None
    home_longitude: float | None
    home_radius_meters: float
    min_confidence: int
    max_horizontal_accuracy_meters: float

    @property
    def home(self) -> tuple[float, float] | None:
        if self.home_latitude is None or self.home_longitude is None:
            return None
        return (self.home_latitude, self.home_longitude)


def _float_or_none(value: str | None) -> float | None:
    return float(value) if value else None


def load_settings() -> Settings:
    return Settings(
        findmy_mode=os.environ.get("FINDMY_MODE", "mock").lower(),
        db_path=os.environ.get("DB_PATH", "/data/larry.db"),
        poll_interval_seconds=int(os.environ.get("POLL_INTERVAL_SECONDS", "300")),
        account_store_path=os.environ.get("FINDMY_ACCOUNT_STORE_PATH", "/data/account.json"),
        anisette_libs_path=os.environ.get("FINDMY_ANISETTE_LIBS_PATH", "/data/ani_libs.bin"),
        anisette_server_url=os.environ.get("FINDMY_ANISETTE_SERVER_URL") or None,
        airtag_key_b64=os.environ.get("FINDMY_AIRTAG_KEY_B64") or None,
        trip_gap_minutes=float(os.environ.get("TRIP_GAP_MINUTES", "45")),
        home_latitude=_float_or_none(os.environ.get("HOME_LATITUDE")),
        home_longitude=_float_or_none(os.environ.get("HOME_LONGITUDE")),
        home_radius_meters=float(os.environ.get("HOME_RADIUS_METERS", "75")),
        min_confidence=int(os.environ.get("MIN_CONFIDENCE", "1")),
        max_horizontal_accuracy_meters=float(
            os.environ.get("MAX_HORIZONTAL_ACCURACY_METERS", "100")
        ),
    )
