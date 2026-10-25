from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from ui_service.config import load_settings
from ui_service.location_client import LocationClient

settings = load_settings()
client = LocationClient(settings.location_service_url)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

app = FastAPI(title="larry-tracker ui-service")


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


@app.get("/api/path")
async def api_path() -> JSONResponse:
    points = await client.get_path()
    return JSONResponse(points)


@app.get("/api/trips")
async def api_trips() -> JSONResponse:
    trips = await client.get_trips()
    return JSONResponse(trips)
