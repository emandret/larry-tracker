"""In-process WebSocket fan-out: tells connected clients that data changed.

Deliberately dumb -- it broadcasts a signal to refetch, not the changed data
itself, so this never becomes a second source of truth for trip computation.
"""

from __future__ import annotations

import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class Broadcaster:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._clients.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._clients.discard(websocket)

    async def broadcast(self, message: dict) -> None:
        dead = []
        for websocket in self._clients:
            try:
                await websocket.send_json(message)
            except Exception:
                logger.warning("dropping dead websocket client", exc_info=True)
                dead.append(websocket)

        for websocket in dead:
            self._clients.discard(websocket)
