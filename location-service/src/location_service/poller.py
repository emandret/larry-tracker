"""Background task that periodically polls the FindMy client and stores new points."""

from __future__ import annotations

import asyncio
import logging

from location_service import db
from location_service.config import Settings
from location_service.findmy_client import FindMyClient

logger = logging.getLogger(__name__)


async def poll_forever(client: FindMyClient, settings: Settings) -> None:
    while True:
        try:
            points = await client.fetch_reports()
            inserted = db.insert_points(settings.db_path, points)
            logger.info("fetched %d point(s), stored %d new", len(points), inserted)
        except Exception:
            logger.exception("poll failed, will retry next interval")

        await asyncio.sleep(settings.poll_interval_seconds)
