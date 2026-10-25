from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    location_service_url: str


def load_settings() -> Settings:
    return Settings(
        location_service_url=os.environ.get(
            "LOCATION_SERVICE_URL", "http://location-service:8001"
        ),
    )
