"""Thin HTTP client for the location-service REST API."""

from __future__ import annotations

import httpx


class LocationClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def get_path(self) -> list[dict]:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=10.0) as client:
            response = await client.get("/locations")
            response.raise_for_status()
            return response.json()

    async def get_latest(self) -> dict | None:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=10.0) as client:
            response = await client.get("/locations/latest")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()

    async def get_trips(self) -> dict:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=10.0) as client:
            response = await client.get("/trips")
            response.raise_for_status()
            return response.json()
